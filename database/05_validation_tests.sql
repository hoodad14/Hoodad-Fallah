
DO $$
DECLARE
    v_table TEXT;
    v_count BIGINT;
    v_tables TEXT[]:=ARRAY[
        'provinces','cities','venues','users','wallets','sport_types','teams',
        'organizers','matches','ticket_categories','tickets','amenities',
        'ticket_amenities','reservations','payment_methods','payments',
        'wallet_transactions','cancellation_policies','cancellation_requests',
        'refunds','seat_change_requests','issued_tickets','report_categories',
        'reports','reservation_status_history'
    ];
BEGIN
    FOREACH v_table IN ARRAY v_tables LOOP
        EXECUTE format('SELECT COUNT(*) FROM %I',v_table) INTO v_count;
        IF v_count<10 THEN
            RAISE EXCEPTION 'Table % has only % rows; at least 10 are required.',
                v_table,v_count;
        END IF;
    END LOOP;
END;
$$;

DO $$
DECLARE v_bad BIGINT;
BEGIN
    WITH actual AS (
        SELECT
            t.id,
            COALESCE((SELECT SUM(r.quantity) FROM reservations r
                      WHERE r.ticket_id=t.id AND r.status='held'),0) AS actual_held,
            COALESCE((SELECT SUM(r.quantity) FROM reservations r
                      WHERE r.ticket_id=t.id AND r.status='paid'),0) AS actual_sold,
            COALESCE((SELECT SUM(scr.quantity) FROM seat_change_requests scr
                      WHERE scr.requested_ticket_id=t.id AND scr.status='pending'),0) AS actual_change_held
        FROM tickets t
    )
    SELECT COUNT(*) INTO v_bad
    FROM tickets t
    JOIN actual a ON a.id=t.id
    WHERE t.held_quantity<>a.actual_held
       OR t.sold_quantity<>a.actual_sold
       OR t.change_held_quantity<>a.actual_change_held
       OR t.available_quantity<0;

    IF v_bad>0 THEN
        RAISE EXCEPTION '% ticket rows have inconsistent inventory counters.',v_bad;
    END IF;
END;
$$;

DO $$
DECLARE v_bad BIGINT;
BEGIN
    SELECT COUNT(*) INTO v_bad
    FROM (
        SELECT t.id,
               COALESCE(SUM(r.quantity) FILTER (WHERE r.status IN ('held','paid')),0)
               + COALESCE((
                    SELECT SUM(scr.quantity)
                    FROM seat_change_requests scr
                    WHERE scr.requested_ticket_id=t.id AND scr.status='pending'
                 ),0) AS active_allocation
        FROM tickets t
        LEFT JOIN reservations r ON r.ticket_id=t.id
        WHERE t.is_numbered
        GROUP BY t.id
        HAVING COALESCE(SUM(r.quantity) FILTER (WHERE r.status IN ('held','paid')),0)
               + COALESCE((
                    SELECT SUM(scr.quantity)
                    FROM seat_change_requests scr
                    WHERE scr.requested_ticket_id=t.id AND scr.status='pending'
                 ),0) > 1
    ) x;

    IF v_bad>0 THEN
        RAISE EXCEPTION '% numbered seats are double allocated.',v_bad;
    END IF;
END;
$$;

DO $$
DECLARE v_bad BIGINT;
BEGIN
    SELECT COUNT(*) INTO v_bad
    FROM payments p
    JOIN reservations r ON r.id=p.reservation_id
    WHERE p.status='successful' AND p.amount<>r.total_amount;
    IF v_bad>0 THEN
        RAISE EXCEPTION '% successful payments have incorrect amounts.',v_bad;
    END IF;
END;
$$;

DO $$
DECLARE v_bad BIGINT;
BEGIN
    SELECT COUNT(*) INTO v_bad
    FROM (
        SELECT r.id,r.status,COUNT(p.id) AS success_count
        FROM reservations r
        LEFT JOIN payments p
          ON p.reservation_id=r.id AND p.status='successful'
        GROUP BY r.id,r.status
        HAVING (r.status IN ('paid','refunded') AND COUNT(p.id)<>1)
            OR (r.status NOT IN ('paid','refunded') AND COUNT(p.id)<>0)
    ) x;
    IF v_bad>0 THEN
        RAISE EXCEPTION '% reservations violate successful-payment cardinality.',v_bad;
    END IF;
END;
$$;

DO $$
DECLARE v_bad BIGINT;
BEGIN
    SELECT COUNT(*) INTO v_bad
    FROM (
        SELECT r.id,r.status,r.quantity,
               COUNT(it.id) AS issued_count,
               COUNT(*) FILTER (WHERE it.status='canceled') AS canceled_count
        FROM reservations r
        LEFT JOIN issued_tickets it ON it.reservation_id=r.id
        GROUP BY r.id,r.status,r.quantity
        HAVING (r.status IN ('paid','refunded') AND COUNT(it.id)<>r.quantity)
            OR (r.status NOT IN ('paid','refunded') AND COUNT(it.id)<>0)
            OR (r.status='refunded'
                AND COUNT(*) FILTER (WHERE it.status='canceled')<>r.quantity)
    ) x;
    IF v_bad>0 THEN
        RAISE EXCEPTION '% reservations have inconsistent issued tickets.',v_bad;
    END IF;
END;
$$;

DO $$
DECLARE v_bad BIGINT;
BEGIN
    SELECT COUNT(*) INTO v_bad
    FROM refunds rf
    JOIN cancellation_requests cr ON cr.id=rf.cancellation_request_id
    JOIN payments p ON p.id=rf.payment_id
    JOIN reservations r ON r.id=cr.reservation_id
    JOIN wallets w ON w.id=rf.wallet_id
    WHERE cr.reservation_id<>p.reservation_id
       OR p.status<>'successful'
       OR w.user_id<>r.user_id
       OR rf.amount+rf.penalty_amount<>p.amount
       OR cr.status<>'processed';

    SELECT v_bad + COUNT(*) INTO v_bad
    FROM (
        SELECT payment_id FROM refunds GROUP BY payment_id HAVING COUNT(*)>1
    ) d;

    IF v_bad>0 THEN
        RAISE EXCEPTION '% refund records are inconsistent.',v_bad;
    END IF;
END;
$$;

DO $$
DECLARE v_bad BIGINT;
BEGIN
    SELECT
        (SELECT COUNT(*) FROM cancellation_requests cr
         JOIN users u ON u.id=cr.reviewed_by WHERE u.role<>'support')
      + (SELECT COUNT(*) FROM seat_change_requests scr
         JOIN users u ON u.id=scr.reviewed_by WHERE u.role<>'support')
      + (SELECT COUNT(*) FROM reports rp
         JOIN users u ON u.id=rp.assigned_to WHERE u.role<>'support')
      + (SELECT COUNT(*) FROM reservations r
         JOIN users u ON u.id=r.canceled_by WHERE u.role<>'support')
    INTO v_bad;

    IF v_bad>0 THEN
        RAISE EXCEPTION '% workflow rows reference non-support actors.',v_bad;
    END IF;
END;
$$;

DO $$
DECLARE
    v_bad BIGINT;
BEGIN
    SELECT COUNT(*)
    INTO v_bad
    FROM seat_change_requests scr
    JOIN reservations r
      ON r.id = scr.reservation_id
    JOIN tickets ot
      ON ot.id = scr.old_ticket_id
    JOIN tickets nt
      ON nt.id = scr.requested_ticket_id
    WHERE scr.requested_by <> r.user_id

       OR scr.quantity <> r.quantity

       OR ot.match_id <> nt.match_id

       OR scr.old_unit_price <> r.unit_price
       OR scr.old_unit_price <> scr.new_unit_price

       OR (nt.is_numbered AND scr.quantity <> 1)

       OR scr.target_hold_expires_at <= scr.requested_at

       OR (
            scr.status = 'pending'
            AND r.ticket_id <> scr.old_ticket_id
       )

       OR (
            scr.status = 'pending'
            AND scr.target_hold_expires_at <= CURRENT_TIMESTAMP
       );

    IF v_bad > 0 THEN
        RAISE EXCEPTION
            '% seat/section-change requests are inconsistent.',
            v_bad;
    END IF;
END;
$$;

DO $$
DECLARE v_bad BIGINT;
BEGIN
    SELECT COUNT(*) INTO v_bad
    FROM (
        SELECT m.id,v.capacity,COALESCE(SUM(t.total_capacity),0) AS allocated
        FROM matches m
        JOIN venues v ON v.id=m.venue_id
        LEFT JOIN tickets t ON t.match_id=m.id
        GROUP BY m.id,v.capacity
        HAVING COALESCE(SUM(t.total_capacity),0)>v.capacity
    ) x;
    IF v_bad>0 THEN
        RAISE EXCEPTION '% matches exceed venue capacity.',v_bad;
    END IF;
END;
$$;

DO $$
DECLARE v_bad BIGINT;
BEGIN
    SELECT COUNT(*) INTO v_bad
    FROM users u
    LEFT JOIN wallets w ON w.user_id=u.id
    WHERE (u.email IS NULL AND u.phone IS NULL)
       OR w.id IS NULL;

    SELECT v_bad
         + (SELECT COUNT(*) FROM (SELECT lower(email::TEXT) FROM users
                                  WHERE email IS NOT NULL GROUP BY lower(email::TEXT)
                                  HAVING COUNT(*)>1) x)
         + (SELECT COUNT(*) FROM (SELECT phone FROM users
                                  WHERE phone IS NOT NULL GROUP BY phone
                                  HAVING COUNT(*)>1) y)
    INTO v_bad;

    IF v_bad>0 THEN
        RAISE EXCEPTION '% user/contact/wallet rules are violated.',v_bad;
    END IF;
END;
$$;

DO $$
DECLARE v_bad BIGINT;
BEGIN
    SELECT COUNT(*) INTO v_bad
    FROM reservations r
    WHERE (r.status='held' AND r.expires_at<=CURRENT_TIMESTAMP)
       OR (r.status='held' AND (r.paid_at IS NOT NULL OR r.canceled_at IS NOT NULL
                               OR r.canceled_by IS NOT NULL OR r.cancellation_reason IS NOT NULL))
       OR (r.status='paid' AND (r.paid_at IS NULL OR r.canceled_at IS NOT NULL
                               OR r.canceled_by IS NOT NULL OR r.cancellation_reason IS NOT NULL))
       OR (r.status='canceled' AND (r.paid_at IS NOT NULL OR r.canceled_at IS NULL
                                   OR r.canceled_by IS NULL OR NULLIF(btrim(r.cancellation_reason),'') IS NULL))
       OR (r.status='expired' AND (r.paid_at IS NOT NULL OR r.canceled_at IS NULL
                                  OR r.canceled_by IS NOT NULL OR NULLIF(btrim(r.cancellation_reason),'') IS NULL))
       OR (r.status='refunded' AND (r.paid_at IS NULL OR r.canceled_at IS NULL
                                   OR r.canceled_at<r.paid_at OR r.canceled_by IS NULL
                                   OR NULLIF(btrim(r.cancellation_reason),'') IS NULL));
    IF v_bad>0 THEN
        RAISE EXCEPTION '% reservations violate lifecycle rules.',v_bad;
    END IF;
END;
$$;

DO $$
DECLARE v_bad BIGINT;
BEGIN
    SELECT COUNT(*) INTO v_bad
    FROM cancellation_requests cr
    JOIN reservations r ON r.id=cr.reservation_id
    WHERE cr.requested_by<>r.user_id
       OR (cr.status='pending' AND (cr.reviewed_by IS NOT NULL OR cr.reviewed_at IS NOT NULL))
       OR (cr.status IN ('approved','rejected','processed')
           AND (cr.reviewed_by IS NULL OR cr.reviewed_at IS NULL
                OR cr.reviewed_at<cr.requested_at))
       OR (cr.estimated_penalty_pct IS NOT NULL
           AND cr.estimated_penalty_pct NOT BETWEEN 0 AND 100)
       OR (cr.estimated_refund IS NOT NULL AND cr.estimated_refund<0);
    IF v_bad>0 THEN
        RAISE EXCEPTION '% cancellation requests are inconsistent.',v_bad;
    END IF;
END;
$$;

DO $$
DECLARE v_bad BIGINT;
BEGIN
    SELECT COUNT(*) INTO v_bad
    FROM reports rp
    LEFT JOIN reservations rr ON rr.id=rp.reservation_id
    LEFT JOIN payments pp ON pp.id=rp.payment_id
    LEFT JOIN reservations pr ON pr.id=pp.reservation_id
    WHERE (rp.reservation_id IS NOT NULL AND rp.reporter_id<>rr.user_id)
       OR (rp.reservation_id IS NOT NULL AND rp.ticket_id IS NOT NULL
           AND rp.ticket_id<>rr.ticket_id)
       OR (rp.payment_id IS NOT NULL AND rp.reservation_id IS NOT NULL
           AND pp.reservation_id<>rp.reservation_id)
       OR (rp.payment_id IS NOT NULL AND rp.reservation_id IS NULL
           AND rp.reporter_id<>pr.user_id)
       OR (rp.payment_id IS NOT NULL AND rp.reservation_id IS NULL
           AND rp.ticket_id IS NOT NULL AND rp.ticket_id<>pr.ticket_id);
    IF v_bad>0 THEN
        RAISE EXCEPTION '% reports have inconsistent links.',v_bad;
    END IF;
END;
$$;

DO $$
DECLARE v_bad BIGINT;
BEGIN
    WITH ledger AS (
        SELECT wt.*,
               SUM(wt.amount) OVER(
                   PARTITION BY wt.wallet_id
                   ORDER BY wt.created_at,wt.id
                   ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
               ) AS calculated_balance
        FROM wallet_transactions wt
    )
    SELECT
        (SELECT COUNT(*)
         FROM (
             SELECT w.id
             FROM wallets w
             LEFT JOIN wallet_transactions wt ON wt.wallet_id=w.id
             GROUP BY w.id,w.balance
             HAVING COALESCE(SUM(wt.amount),0)<>w.balance
         ) x)
      + (SELECT COUNT(*) FROM ledger WHERE balance_after<>calculated_balance)
    INTO v_bad;

    IF v_bad>0 THEN
        RAISE EXCEPTION '% wallet ledger checks failed.',v_bad;
    END IF;
END;
$$;

DO $$
DECLARE v_bad BIGINT;
BEGIN
    WITH first_last AS (
        SELECT DISTINCT ON (h.reservation_id)
               h.reservation_id,
               first_value(h.new_status) OVER (
                   PARTITION BY h.reservation_id ORDER BY h.changed_at,h.id
               ) AS first_status,
               first_value(h.new_status) OVER (
                   PARTITION BY h.reservation_id ORDER BY h.changed_at DESC,h.id DESC
               ) AS last_status
        FROM reservation_status_history h
        ORDER BY h.reservation_id,h.changed_at,h.id
    )
    SELECT COUNT(*) INTO v_bad
    FROM reservations r
    LEFT JOIN first_last fl ON fl.reservation_id=r.id
    WHERE fl.reservation_id IS NULL
       OR fl.first_status<>'held'
       OR fl.last_status<>r.status;

    IF v_bad>0 THEN
        RAISE EXCEPTION '% reservation audit histories are incomplete.',v_bad;
    END IF;
END;
$$;

DO $$
DECLARE v_required INTEGER; v_business INTEGER;
BEGIN
    SELECT COUNT(DISTINCT p.proname) INTO v_required
    FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
    WHERE n.nspname=current_schema()
      AND p.proname IN (
        'sp_get_purchased_tickets_by_contact',
        'sp_get_users_canceled_by_support',
        'sp_get_purchased_tickets_by_city',
        'sp_search_tickets',
        'sp_get_same_city_users',
        'sp_top_buyers_since',
        'sp_get_canceled_tickets_by_sport',
        'sp_top_reporters_by_subject'
      );

    SELECT COUNT(DISTINCT p.proname) INTO v_business
    FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
    WHERE n.nspname=current_schema()
      AND p.proname IN (
        'fn_get_penalty_percentage','release_pending_seat_change_holds',
        'expire_pending_seat_change_requests','expire_pending_reservations',
        'reserve_ticket','process_payment','top_up_wallet',
        'request_cancellation','review_cancellation',
        'request_seat_change','review_seat_change','deactivate_user'
      );

    IF v_required<>8 OR v_business<>12 THEN
        RAISE EXCEPTION 'Function coverage failed: mandatory %, business %.',
            v_required,v_business;
    END IF;
END;
$$;

DO $$
DECLARE v_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_count
    FROM pg_indexes
    WHERE schemaname=current_schema()
      AND indexname IN (
        'uq_numbered_ticket_seat','uq_general_ticket_bucket',
        'uq_payments_one_success_per_reservation','uq_refunds_payment',
        'uq_wallet_purchase_per_payment','uq_wallet_refund_per_payment',
        'uq_cancellation_one_pending','uq_seat_change_one_pending',
        'idx_matches_search','idx_tickets_available',
        'idx_reservations_expiring_holds','idx_seat_change_expiring_holds',
        'idx_payments_status_paid_at','idx_users_full_name_trgm',
        'idx_teams_name_trgm','idx_venues_name_trgm'
      );
    IF v_count<>16 THEN
        RAISE EXCEPTION 'Only % of 16 critical indexes exist.',v_count;
    END IF;
END;
$$;

DO $$
DECLARE v_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_count
    FROM information_schema.views
    WHERE table_schema=current_schema()
      AND table_name IN (
        'v_ticket_catalog','v_purchased_tickets',
        'football_details','volleyball_details','basketball_details'
      );
    IF v_count<>5 THEN
        RAISE EXCEPTION 'Only % of 5 required views exist.',v_count;
    END IF;
END;
$$;

DO $$
DECLARE v_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_count
    FROM pg_trigger tg
    JOIN pg_class c ON c.oid=tg.tgrelid
    JOIN pg_namespace n ON n.oid=c.relnamespace
    WHERE n.nspname=current_schema()
      AND NOT tg.tgisinternal
      AND tg.tgname IN (
        'assert_ticket_inventory_from_tickets',
        'assert_ticket_inventory_from_reservations',
        'assert_ticket_inventory_from_seat_changes',
        'assert_wallet_balance_from_wallets',
        'assert_wallet_balance_from_ledger',
        'assert_financial_lifecycle_from_reservations',
        'assert_financial_lifecycle_from_payments',
        'assert_financial_lifecycle_from_issued_tickets',
        'assert_financial_lifecycle_from_refunds'
      );
    IF v_count<>9 THEN
        RAISE EXCEPTION 'Only % of 9 critical deferred integrity triggers exist.',v_count;
    END IF;
END;
$$;

DO $$
DECLARE
    v_table_exists BOOLEAN;
    v_function_exists BOOLEAN;
    v_index_count INTEGER;
    v_trigger_count INTEGER;
BEGIN
    SELECT to_regclass(current_schema() || '.search_sync_outbox') IS NOT NULL
    INTO v_table_exists;

    SELECT to_regprocedure(
        current_schema() || '.enqueue_ticket_search_sync(bigint)'
    ) IS NOT NULL
    INTO v_function_exists;

    SELECT COUNT(*) INTO v_index_count
    FROM pg_indexes
    WHERE schemaname=current_schema()
      AND indexname IN (
        'uq_search_outbox_pending_ticket',
        'idx_search_outbox_available',
        'idx_search_outbox_processed'
      );

    SELECT COUNT(*) INTO v_trigger_count
    FROM pg_trigger tg
    JOIN pg_class c ON c.oid=tg.tgrelid
    JOIN pg_namespace n ON n.oid=c.relnamespace
    WHERE n.nspname=current_schema()
      AND NOT tg.tgisinternal
      AND tg.tgname IN (
        'search_sync_ticket','search_sync_ticket_amenity',
        'search_sync_match','search_sync_team','search_sync_sport',
        'search_sync_venue','search_sync_city','search_sync_province',
        'search_sync_organizer','search_sync_category','search_sync_amenity'
      );

    IF NOT v_table_exists OR NOT v_function_exists
       OR v_index_count<>3 OR v_trigger_count<>11 THEN
        RAISE EXCEPTION
            'Search sync coverage failed: table %, function %, indexes %, triggers %.',
            v_table_exists,v_function_exists,v_index_count,v_trigger_count;
    END IF;
END;
$$;

BEGIN;

DO $$
DECLARE
    v_rejected BOOLEAN;
BEGIN
    v_rejected:=FALSE;
    BEGIN
        UPDATE tickets SET price=-1 WHERE id=1;
    EXCEPTION WHEN OTHERS THEN
        v_rejected:=TRUE;
    END;
    IF NOT v_rejected THEN RAISE EXCEPTION 'Negative ticket price was accepted.'; END IF;

    v_rejected:=FALSE;
    BEGIN
        UPDATE users
        SET email=(SELECT email FROM users WHERE id=6)
        WHERE id=7;
    EXCEPTION WHEN OTHERS THEN
        v_rejected:=TRUE;
    END;
    IF NOT v_rejected THEN RAISE EXCEPTION 'Duplicate email was accepted.'; END IF;

    v_rejected:=FALSE;
    BEGIN
        UPDATE wallet_transactions SET description='tampered' WHERE id=1;
    EXCEPTION WHEN OTHERS THEN
        v_rejected:=TRUE;
    END;
    IF NOT v_rejected THEN RAISE EXCEPTION 'Append-only wallet ledger was mutable.'; END IF;
END;
$$;

DO $$
DECLARE v_rejected BOOLEAN:=FALSE;
BEGIN
    BEGIN
        UPDATE tickets SET held_quantity=held_quantity+1 WHERE id=1;
        SET CONSTRAINTS ALL IMMEDIATE;
    EXCEPTION WHEN OTHERS THEN
        v_rejected:=TRUE;
    END;
    SET CONSTRAINTS ALL DEFERRED;
    IF NOT v_rejected THEN
        RAISE EXCEPTION 'Direct inconsistent inventory-counter update was accepted.';
    END IF;
END;
$$;

DO $$
DECLARE v_rejected BOOLEAN:=FALSE;
BEGIN
    BEGIN
        INSERT INTO payments
            (reservation_id,payment_method_id,amount,status,transaction_ref,created_at,paid_at)
        SELECT r.id,1,r.total_amount,'successful','VALIDATION-ILLEGAL-SUCCESS',
               CURRENT_TIMESTAMP,CURRENT_TIMESTAMP
        FROM reservations r
        WHERE r.id=9 AND r.status='held';

        SET CONSTRAINTS ALL IMMEDIATE;
    EXCEPTION WHEN OTHERS THEN
        v_rejected:=TRUE;
    END;
    SET CONSTRAINTS ALL DEFERRED;
    IF NOT v_rejected THEN
        RAISE EXCEPTION 'A held reservation accepted a successful payment without a paid lifecycle.';
    END IF;
END;
$$;

DO $$
DECLARE
    v_reservation_id BIGINT;
    v_payment_id BIGINT;
    v_request_id BIGINT;
    v_initial_wallet NUMERIC(16,2);
    v_final_wallet NUMERIC(16,2);
    v_status VARCHAR(20);
BEGIN
    SELECT balance INTO v_initial_wallet FROM wallets WHERE user_id=24;

    SELECT x.reservation_id INTO v_reservation_id
    FROM reserve_ticket(24,1,1) AS x;

    SELECT x.payment_id INTO v_payment_id
    FROM process_payment(24,v_reservation_id,'wallet') AS x;

    SELECT x.request_id INTO v_request_id
    FROM request_cancellation(24,v_reservation_id,'Validation workflow') AS x;

    PERFORM * FROM review_cancellation(1,v_request_id,TRUE,'Validation approved');

    SELECT status INTO v_status FROM reservations WHERE id=v_reservation_id;
    SELECT balance INTO v_final_wallet FROM wallets WHERE user_id=24;

    IF v_status<>'refunded' THEN
        RAISE EXCEPTION 'End-to-end cancellation ended with status %.',v_status;
    END IF;
    IF v_initial_wallet<>v_final_wallet THEN
        RAISE EXCEPTION 'Wallet was not restored after zero-penalty validation refund.';
    END IF;
    IF NOT EXISTS(SELECT 1 FROM refunds WHERE payment_id=v_payment_id AND status='completed') THEN
        RAISE EXCEPTION 'Completed refund was not created.';
    END IF;

    SET CONSTRAINTS ALL IMMEDIATE;
    SET CONSTRAINTS ALL DEFERRED;
END;
$$;

DO $$
DECLARE
    v_request_id BIGINT;
    v_old_sold INTEGER;
    v_new_sold INTEGER;
    v_current_ticket BIGINT;
BEGIN
    SELECT sold_quantity INTO v_old_sold FROM tickets WHERE id=31;
    SELECT sold_quantity INTO v_new_sold FROM tickets WHERE id=32;

    v_request_id:=request_seat_change(24,40,32);

    IF (SELECT change_held_quantity FROM tickets WHERE id=32)<1 THEN
        RAISE EXCEPTION 'Destination seat was not held.';
    END IF;

    PERFORM * FROM review_seat_change(1,v_request_id,TRUE,'Validation approved');
    SELECT ticket_id INTO v_current_ticket FROM reservations WHERE id=40;

    IF v_current_ticket<>32
       OR (SELECT sold_quantity FROM tickets WHERE id=31)<>v_old_sold-1
       OR (SELECT sold_quantity FROM tickets WHERE id=32)<>v_new_sold+1
       OR (SELECT change_held_quantity FROM tickets WHERE id=32)<>0 THEN
        RAISE EXCEPTION 'Seat-change inventory transfer failed.';
    END IF;

    SET CONSTRAINTS ALL IMMEDIATE;
    SET CONSTRAINTS ALL DEFERRED;
END;
$$;

DO $$
DECLARE
    v_reservation_id BIGINT;
    v_before INTEGER;
    v_after INTEGER;
BEGIN
    SELECT held_quantity INTO v_before FROM tickets WHERE id=1;

    SELECT x.reservation_id INTO v_reservation_id
    FROM reserve_ticket(25,1,1) AS x;

    UPDATE reservations
    SET reserved_at=CURRENT_TIMESTAMP-INTERVAL '20 minutes',
        expires_at=CURRENT_TIMESTAMP-INTERVAL '10 minutes'
    WHERE id=v_reservation_id;

    PERFORM expire_pending_reservations();

    SELECT held_quantity INTO v_after FROM tickets WHERE id=1;
    IF (SELECT status FROM reservations WHERE id=v_reservation_id)<>'expired'
       OR v_after<>v_before THEN
        RAISE EXCEPTION 'Reservation expiration did not restore inventory.';
    END IF;

    SET CONSTRAINTS ALL IMMEDIATE;
    SET CONSTRAINTS ALL DEFERRED;
END;
$$;

DO $$
DECLARE
    v_category_id BIGINT;
    v_reservation_id BIGINT;
    v_rejected BOOLEAN:=FALSE;
BEGIN
    SELECT ticket_category_id INTO v_category_id FROM tickets WHERE id=1;

    UPDATE ticket_categories SET is_active=FALSE WHERE id=v_category_id;
    BEGIN
        PERFORM * FROM reserve_ticket(25,1,1);
    EXCEPTION WHEN OTHERS THEN
        v_rejected:=TRUE;
    END;
    UPDATE ticket_categories SET is_active=TRUE WHERE id=v_category_id;
    IF NOT v_rejected THEN
        RAISE EXCEPTION 'Reservation was accepted for an inactive ticket category.';
    END IF;

    SELECT x.reservation_id INTO v_reservation_id
    FROM reserve_ticket(25,1,1) AS x;

    v_rejected:=FALSE;
    UPDATE ticket_categories SET is_active=FALSE WHERE id=v_category_id;
    BEGIN
        PERFORM * FROM process_payment(25,v_reservation_id,'local_gateway');
    EXCEPTION WHEN OTHERS THEN
        v_rejected:=TRUE;
    END;
    UPDATE ticket_categories SET is_active=TRUE WHERE id=v_category_id;
    IF NOT v_rejected THEN
        RAISE EXCEPTION 'Payment was accepted for an inactive ticket category.';
    END IF;

    UPDATE reservations
    SET reserved_at=CURRENT_TIMESTAMP-INTERVAL '20 minutes',
        expires_at=CURRENT_TIMESTAMP-INTERVAL '10 minutes'
    WHERE id=v_reservation_id;
    PERFORM expire_pending_reservations();

    SET CONSTRAINTS ALL IMMEDIATE;
    SET CONSTRAINTS ALL DEFERRED;
END;
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema='public' AND table_name='users' AND column_name='email_verified_at'
    ) OR NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema='public' AND table_name='users' AND column_name='phone_verified_at'
    ) OR NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema='public' AND table_name='users' AND column_name='last_login_at'
    ) THEN
        RAISE EXCEPTION 'Authentication verification columns are missing.';
    END IF;

    IF EXISTS (
        SELECT 1 FROM users
        WHERE (email IS NOT NULL AND email_verified_at IS NULL)
           OR (phone IS NOT NULL AND phone_verified_at IS NULL)
    ) THEN
        RAISE EXCEPTION 'Seed contacts were not marked verified.';
    END IF;

    IF EXISTS (
        SELECT 1 FROM users
        WHERE password_hash IS NULL
           OR password_hash IN ('Demo@123','StrongPass1','TestPass1')
    ) THEN
        RAISE EXCEPTION 'A plaintext or missing seed password was detected.';
    END IF;
END;
$$;

DO $$
DECLARE
    v_conflicts INTEGER;
    v_upcoming_matches INTEGER;
    v_distinct_teams INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_conflicts
    FROM matches a
    JOIN matches b ON a.id<b.id AND a.starts_at::date=b.starts_at::date
    WHERE a.home_team_id IN (b.home_team_id,b.away_team_id)
       OR a.away_team_id IN (b.home_team_id,b.away_team_id);
    IF v_conflicts<>0 THEN
        RAISE EXCEPTION 'Same-day team scheduling conflict detected: %',v_conflicts;
    END IF;
    SELECT COUNT(*) INTO v_upcoming_matches FROM matches WHERE status='scheduled' AND starts_at>CURRENT_TIMESTAMP;
    IF v_upcoming_matches<55 THEN
        RAISE EXCEPTION 'Expanded upcoming match catalog is unexpectedly small: %',v_upcoming_matches;
    END IF;
    SELECT COUNT(DISTINCT team_id) INTO v_distinct_teams
    FROM (
        SELECT home_team_id AS team_id FROM matches WHERE starts_at>CURRENT_TIMESTAMP
        UNION
        SELECT away_team_id FROM matches WHERE starts_at>CURRENT_TIMESTAMP
    ) q;
    IF v_distinct_teams<45 THEN
        RAISE EXCEPTION 'Expanded match catalog does not contain enough distinct teams: %',v_distinct_teams;
    END IF;
END;
$$;

ROLLBACK;

SELECT 'spectators_without_reservation' AS check_name,COUNT(*) AS result_count
FROM users u
WHERE u.role='spectator'
  AND NOT EXISTS(SELECT 1 FROM reservations r WHERE r.user_id=u.id)
UNION ALL
SELECT 'users_with_successful_purchase',COUNT(DISTINCT r.user_id)
FROM reservations r JOIN payments p ON p.reservation_id=r.id AND p.status='successful'
UNION ALL
SELECT 'support_users',COUNT(*) FROM users WHERE role='support'
UNION ALL
SELECT 'canceled_or_refunded_reservations',COUNT(*)
FROM reservations WHERE status IN ('canceled','refunded')
UNION ALL
SELECT 'pending_destination_holds',COUNT(*)
FROM seat_change_requests WHERE status='pending'
UNION ALL
SELECT 'reports',COUNT(*) FROM reports
UNION ALL
SELECT 'mandatory_stored_functions',COUNT(DISTINCT proname)
FROM pg_proc
WHERE proname IN (
    'sp_get_purchased_tickets_by_contact',
    'sp_get_users_canceled_by_support',
    'sp_get_purchased_tickets_by_city','sp_search_tickets',
    'sp_get_same_city_users','sp_top_buyers_since',
    'sp_get_canceled_tickets_by_sport','sp_top_reporters_by_subject'
);

EXPLAIN (ANALYZE,BUFFERS)
SELECT t.id,m.starts_at,t.price,t.available_quantity
FROM tickets t
JOIN matches m ON m.id=t.match_id
WHERE m.sport_type_id=(SELECT id FROM sport_types WHERE code='football')
  AND m.is_active
  AND m.starts_at>=CURRENT_TIMESTAMP
  AND t.is_active
  AND t.available_quantity>0
ORDER BY m.starts_at,t.price
LIMIT 20;

EXPLAIN (ANALYZE,BUFFERS)
SELECT id,name
FROM teams
WHERE lower(name) LIKE '%tehran%';
