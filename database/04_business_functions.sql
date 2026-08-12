
BEGIN;


CREATE OR REPLACE FUNCTION fn_get_penalty_percentage(
    p_ticket_id BIGINT,
    p_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
)
RETURNS NUMERIC(5,2)
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_organizer_id BIGINT;
    v_starts_at TIMESTAMPTZ;
    v_hours NUMERIC;
    v_penalty NUMERIC(5,2);
BEGIN
    IF p_ticket_id IS NULL OR p_at IS NULL THEN
        RAISE EXCEPTION 'Ticket and evaluation time are required.';
    END IF;

    SELECT m.organizer_id,m.starts_at
    INTO v_organizer_id,v_starts_at
    FROM tickets t
    JOIN matches m ON m.id=t.match_id
    WHERE t.id=p_ticket_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Ticket % does not exist.',p_ticket_id;
    END IF;

    v_hours:=EXTRACT(EPOCH FROM (v_starts_at-p_at))/3600.0;
    IF v_hours<=0 THEN
        RETURN 100.00;
    END IF;

    SELECT cp.penalty_percentage
    INTO v_penalty
    FROM cancellation_policies cp
    WHERE cp.organizer_id=v_organizer_id
      AND cp.hours_before_match<=v_hours
    ORDER BY cp.hours_before_match DESC
    LIMIT 1;

    RETURN COALESCE(v_penalty,0.00);
END;
$$;



CREATE OR REPLACE FUNCTION release_pending_seat_change_holds(
    p_reservation_id BIGINT,
    p_note TEXT DEFAULT 'Destination hold released automatically'
)
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    rec RECORD;
    v_count INTEGER:=0;
BEGIN
    FOR rec IN
        SELECT id,requested_ticket_id,quantity
        FROM seat_change_requests
        WHERE reservation_id=p_reservation_id
          AND status='pending'
        ORDER BY id
        FOR UPDATE
    LOOP
        UPDATE tickets
        SET change_held_quantity=change_held_quantity-rec.quantity
        WHERE id=rec.requested_ticket_id
          AND change_held_quantity>=rec.quantity;

        IF NOT FOUND THEN
            RAISE EXCEPTION 'Destination-hold counter is inconsistent for seat-change request %.',rec.id;
        END IF;

        UPDATE seat_change_requests
        SET status='expired',
            review_note=COALESCE(NULLIF(btrim(p_note),''),'Destination hold released automatically'),
            reviewed_at=CURRENT_TIMESTAMP,
            reviewed_by=NULL
        WHERE id=rec.id;

        v_count:=v_count+1;
    END LOOP;

    RETURN v_count;
END;
$$;


CREATE OR REPLACE FUNCTION expire_pending_seat_change_requests()
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    rec RECORD;
    v_count INTEGER:=0;
BEGIN
    FOR rec IN
        SELECT id,reservation_id,requested_ticket_id,quantity
        FROM seat_change_requests
        WHERE status='pending'
          AND target_hold_expires_at<=CURRENT_TIMESTAMP
        ORDER BY target_hold_expires_at,id
        FOR UPDATE SKIP LOCKED
    LOOP
        UPDATE tickets
        SET change_held_quantity=change_held_quantity-rec.quantity
        WHERE id=rec.requested_ticket_id
          AND change_held_quantity>=rec.quantity;

        IF NOT FOUND THEN
            RAISE EXCEPTION 'Destination-hold counter is inconsistent for seat-change request %.',rec.id;
        END IF;

        UPDATE seat_change_requests
        SET status='expired',
            review_note='Destination hold expired before support review',
            reviewed_at=CURRENT_TIMESTAMP,
            reviewed_by=NULL
        WHERE id=rec.id;

        v_count:=v_count+1;
    END LOOP;

    RETURN v_count;
END;
$$;


CREATE OR REPLACE FUNCTION expire_pending_reservations()
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    rec RECORD;
    v_count INTEGER:=0;
BEGIN
    FOR rec IN
        SELECT r.id,r.ticket_id,r.quantity
        FROM reservations r
        WHERE r.status='held'
          AND r.expires_at<=CURRENT_TIMESTAMP
        ORDER BY r.expires_at,r.id
        FOR UPDATE SKIP LOCKED
    LOOP
        PERFORM release_pending_seat_change_holds(
            rec.id,
            'Destination hold released because reservation expired'
        );

        UPDATE tickets
        SET held_quantity=held_quantity-rec.quantity
        WHERE id=rec.ticket_id
          AND held_quantity>=rec.quantity;

        IF NOT FOUND THEN
            RAISE EXCEPTION 'Ticket held counter is inconsistent for reservation %.',rec.id;
        END IF;

        UPDATE reservations
        SET status='expired',
            canceled_at=CURRENT_TIMESTAMP,
            canceled_by=NULL,
            cancellation_reason='Automatic expiration after payment timeout'
        WHERE id=rec.id;

        v_count:=v_count+1;
    END LOOP;

    RETURN v_count;
END;
$$;


CREATE OR REPLACE FUNCTION reserve_ticket(
    p_user_id BIGINT,
    p_ticket_id BIGINT,
    p_quantity INTEGER DEFAULT 1
)
RETURNS TABLE (
    reservation_id BIGINT,
    reservation_status VARCHAR,
    expires_at TIMESTAMPTZ,
    total_amount NUMERIC
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_user RECORD;
    v_ticket RECORD;
    v_reservation_id BIGINT;
    v_expires_at TIMESTAMPTZ;
BEGIN
    IF p_user_id IS NULL OR p_ticket_id IS NULL THEN
        RAISE EXCEPTION 'User and ticket are required.';
    END IF;
    IF p_quantity IS NULL OR p_quantity<=0 THEN
        RAISE EXCEPTION 'Quantity must be greater than zero.';
    END IF;

    SELECT role,is_active
    INTO v_user
    FROM users
    WHERE id=p_user_id
    FOR KEY SHARE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'User % does not exist.',p_user_id;
    END IF;
    IF v_user.role<>'spectator' OR NOT v_user.is_active THEN
        RAISE EXCEPTION 'User % is not an active spectator.',p_user_id;
    END IF;

    SELECT
        t.id,t.price,t.is_numbered,t.available_quantity,t.is_active,
        t.sale_starts_at,t.sale_ends_at,
        m.starts_at,m.status AS match_status,m.is_active AS match_active,
        v.is_active AS venue_active,o.is_active AS organizer_active,
        st.is_active AS sport_active,ht.is_active AS home_team_active,
        at.is_active AS away_team_active,tc.is_active AS category_active
    INTO v_ticket
    FROM tickets t
    JOIN matches m ON m.id=t.match_id
    JOIN sport_types st ON st.id=m.sport_type_id
    JOIN teams ht ON ht.id=m.home_team_id
    JOIN teams at ON at.id=m.away_team_id
    JOIN venues v ON v.id=m.venue_id
    JOIN organizers o ON o.id=m.organizer_id
    JOIN ticket_categories tc ON tc.id=t.ticket_category_id
    WHERE t.id=p_ticket_id
    FOR UPDATE OF t,m;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Ticket % does not exist.',p_ticket_id;
    END IF;
    IF NOT v_ticket.is_active OR NOT v_ticket.match_active
       OR NOT v_ticket.venue_active OR NOT v_ticket.organizer_active
       OR NOT v_ticket.sport_active OR NOT v_ticket.home_team_active
       OR NOT v_ticket.away_team_active OR NOT v_ticket.category_active THEN
        RAISE EXCEPTION 'Ticket or a required catalog entity is inactive.';
    END IF;
    IF v_ticket.match_status NOT IN ('scheduled','postponed') THEN
        RAISE EXCEPTION 'Match status % does not allow reservation.',v_ticket.match_status;
    END IF;
    IF v_ticket.starts_at<=CURRENT_TIMESTAMP THEN
        RAISE EXCEPTION 'The match has already started.';
    END IF;
    IF v_ticket.sale_starts_at IS NOT NULL
       AND CURRENT_TIMESTAMP<v_ticket.sale_starts_at THEN
        RAISE EXCEPTION 'Ticket sale has not started.';
    END IF;
    IF v_ticket.sale_ends_at IS NOT NULL
       AND CURRENT_TIMESTAMP>=v_ticket.sale_ends_at THEN
        RAISE EXCEPTION 'Ticket sale has ended.';
    END IF;
    IF v_ticket.is_numbered AND p_quantity<>1 THEN
        RAISE EXCEPTION 'A numbered seat must be reserved with quantity 1.';
    END IF;
    IF v_ticket.available_quantity<p_quantity THEN
        RAISE EXCEPTION 'Insufficient inventory. Available %, requested %.',
            v_ticket.available_quantity,p_quantity;
    END IF;

    
    v_expires_at:=LEAST(
        CURRENT_TIMESTAMP+INTERVAL '10 minutes',
        v_ticket.starts_at-INTERVAL '1 second',
        COALESCE(v_ticket.sale_ends_at,'infinity'::TIMESTAMPTZ)
    );
    IF v_expires_at<=CURRENT_TIMESTAMP THEN
        RAISE EXCEPTION 'There is not enough time to create a valid reservation hold.';
    END IF;

    UPDATE tickets
    SET held_quantity=held_quantity+p_quantity
    WHERE id=p_ticket_id;

    INSERT INTO reservations
        (user_id,ticket_id,status,quantity,unit_price,reserved_at,expires_at)
    VALUES
        (p_user_id,p_ticket_id,'held',p_quantity,v_ticket.price,
         CURRENT_TIMESTAMP,v_expires_at)
    RETURNING id INTO v_reservation_id;

    RETURN QUERY
    SELECT v_reservation_id,'held'::VARCHAR,v_expires_at,
           ROUND(v_ticket.price*p_quantity,2);
END;
$$;



CREATE OR REPLACE FUNCTION process_payment(
    p_user_id BIGINT,
    p_reservation_id BIGINT,
    p_payment_method_code TEXT
)
RETURNS TABLE (
    payment_id BIGINT,
    payment_status VARCHAR,
    amount NUMERIC,
    transaction_ref VARCHAR,
    reservation_status VARCHAR
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_reservation RECORD;
    v_existing RECORD;
    v_method_id BIGINT;
    v_method_code VARCHAR(50);
    v_payment_id BIGINT;
    v_reference VARCHAR(100):='PAY-'||upper(replace(gen_random_uuid()::TEXT,'-',''));
    v_wallet_id BIGINT;
    v_wallet_balance NUMERIC(16,2);
    v_new_balance NUMERIC(16,2);
BEGIN
    IF p_user_id IS NULL OR p_reservation_id IS NULL THEN
        RAISE EXCEPTION 'User and reservation are required.';
    END IF;
    IF p_payment_method_code IS NULL OR btrim(p_payment_method_code)='' THEN
        RAISE EXCEPTION 'Payment method code is required.';
    END IF;
    IF NOT EXISTS(
        SELECT 1 FROM users
        WHERE id=p_user_id AND role='spectator' AND is_active
    ) THEN
        RAISE EXCEPTION 'User % is not an active spectator.',p_user_id;
    END IF;

    SELECT
        r.id,r.user_id,r.ticket_id,r.status,r.quantity,r.total_amount,r.expires_at,
        t.held_quantity,t.is_active AS ticket_active,
        m.is_active AS match_active,m.status AS match_status,m.starts_at,
        v.is_active AS venue_active,o.is_active AS organizer_active,
        st.is_active AS sport_active,ht.is_active AS home_team_active,
        at.is_active AS away_team_active,tc.is_active AS category_active
    INTO v_reservation
    FROM reservations r
    JOIN tickets t ON t.id=r.ticket_id
    JOIN matches m ON m.id=t.match_id
    JOIN sport_types st ON st.id=m.sport_type_id
    JOIN teams ht ON ht.id=m.home_team_id
    JOIN teams at ON at.id=m.away_team_id
    JOIN venues v ON v.id=m.venue_id
    JOIN organizers o ON o.id=m.organizer_id
    JOIN ticket_categories tc ON tc.id=t.ticket_category_id
    WHERE r.id=p_reservation_id
    FOR UPDATE OF r,t,m;

    IF NOT FOUND OR v_reservation.user_id<>p_user_id THEN
        RAISE EXCEPTION 'Reservation % does not belong to user %.',p_reservation_id,p_user_id;
    END IF;

    SELECT p.id,p.amount,p.transaction_ref
    INTO v_existing
    FROM payments p
    WHERE p.reservation_id=p_reservation_id
      AND p.status='successful';

    IF FOUND THEN
        
        
        RETURN QUERY
        SELECT v_existing.id,'successful'::VARCHAR,v_existing.amount,
               v_existing.transaction_ref,v_reservation.status::VARCHAR;
        RETURN;
    END IF;

    SELECT id,code
    INTO v_method_id,v_method_code
    FROM payment_methods
    WHERE lower(code)=lower(btrim(p_payment_method_code))
      AND is_active;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Active payment method % was not found.',p_payment_method_code;
    END IF;

    IF v_reservation.status<>'held' THEN
        RAISE EXCEPTION 'Reservation status % cannot be paid.',v_reservation.status;
    END IF;

    IF v_reservation.expires_at<=CURRENT_TIMESTAMP THEN
        PERFORM release_pending_seat_change_holds(
            p_reservation_id,
            'Destination hold released because reservation expired before payment'
        );

        UPDATE tickets
        SET held_quantity=held_quantity-v_reservation.quantity
        WHERE id=v_reservation.ticket_id
          AND held_quantity>=v_reservation.quantity;

        IF NOT FOUND THEN
            RAISE EXCEPTION 'Ticket held counter is inconsistent for reservation %.',p_reservation_id;
        END IF;

        UPDATE reservations
        SET status='expired',
            canceled_at=CURRENT_TIMESTAMP,
            canceled_by=NULL,
            cancellation_reason='Reservation expired before payment'
        WHERE id=p_reservation_id;

        INSERT INTO payments
            (reservation_id,payment_method_id,amount,status,transaction_ref,
             failure_reason,created_at)
        VALUES
            (p_reservation_id,v_method_id,v_reservation.total_amount,'failed',
             v_reference,'Reservation expired before payment',CURRENT_TIMESTAMP)
        RETURNING id INTO v_payment_id;

        RETURN QUERY
        SELECT v_payment_id,'failed'::VARCHAR,v_reservation.total_amount,
               v_reference,'expired'::VARCHAR;
        RETURN;
    END IF;

    IF NOT v_reservation.ticket_active OR NOT v_reservation.match_active
       OR NOT v_reservation.venue_active OR NOT v_reservation.organizer_active
       OR NOT v_reservation.sport_active OR NOT v_reservation.home_team_active
       OR NOT v_reservation.away_team_active OR NOT v_reservation.category_active THEN
        RAISE EXCEPTION 'Ticket or a required catalog entity is inactive.';
    END IF;
    IF v_reservation.match_status NOT IN ('scheduled','postponed') THEN
        RAISE EXCEPTION 'Match status % does not allow payment.',v_reservation.match_status;
    END IF;
    IF v_reservation.starts_at<=CURRENT_TIMESTAMP THEN
        RAISE EXCEPTION 'Payment is not allowed after the match has started.';
    END IF;
    IF v_reservation.held_quantity<v_reservation.quantity THEN
        RAISE EXCEPTION 'Ticket held counter is inconsistent for reservation %.',p_reservation_id;
    END IF;
    IF EXISTS(SELECT 1 FROM issued_tickets WHERE reservation_id=p_reservation_id) THEN
        RAISE EXCEPTION 'Held reservation % already has issued ticket rows.',p_reservation_id;
    END IF;

    IF v_method_code='wallet' AND v_reservation.total_amount>0 THEN
        SELECT id,balance
        INTO v_wallet_id,v_wallet_balance
        FROM wallets
        WHERE user_id=p_user_id
        FOR UPDATE;

        IF NOT FOUND OR v_wallet_balance<v_reservation.total_amount THEN
            INSERT INTO payments
                (reservation_id,payment_method_id,amount,status,transaction_ref,
                 failure_reason,created_at)
            VALUES
                (p_reservation_id,v_method_id,v_reservation.total_amount,'failed',
                 v_reference,'Insufficient wallet balance',CURRENT_TIMESTAMP)
            RETURNING id INTO v_payment_id;

            RETURN QUERY
            SELECT v_payment_id,'failed'::VARCHAR,v_reservation.total_amount,
                   v_reference,'held'::VARCHAR;
            RETURN;
        END IF;

        UPDATE wallets
        SET balance=balance-v_reservation.total_amount
        WHERE id=v_wallet_id
        RETURNING balance INTO v_new_balance;
    END IF;

    INSERT INTO payments
        (reservation_id,payment_method_id,amount,status,transaction_ref,created_at,paid_at)
    VALUES
        (p_reservation_id,v_method_id,v_reservation.total_amount,'successful',
         v_reference,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)
    RETURNING id INTO v_payment_id;

    IF v_method_code='wallet' AND v_reservation.total_amount>0 THEN
        INSERT INTO wallet_transactions
            (wallet_id,payment_id,transaction_type,amount,balance_after,
             reference_code,description)
        VALUES
            (v_wallet_id,v_payment_id,'purchase',-v_reservation.total_amount,
             v_new_balance,'WT-'||v_reference,'Ticket purchase');
    END IF;

    UPDATE tickets
    SET held_quantity=held_quantity-v_reservation.quantity,
        sold_quantity=sold_quantity+v_reservation.quantity
    WHERE id=v_reservation.ticket_id
      AND held_quantity>=v_reservation.quantity;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Ticket held counter is inconsistent for reservation %.',p_reservation_id;
    END IF;

    UPDATE reservations
    SET status='paid',paid_at=CURRENT_TIMESTAMP,
        canceled_at=NULL,canceled_by=NULL,cancellation_reason=NULL
    WHERE id=p_reservation_id;

    INSERT INTO issued_tickets(reservation_id,status,issued_at)
    SELECT p_reservation_id,'active',CURRENT_TIMESTAMP
    FROM generate_series(1,v_reservation.quantity);

    RETURN QUERY
    SELECT v_payment_id,'successful'::VARCHAR,v_reservation.total_amount,
           v_reference,'paid'::VARCHAR;
END;
$$;


CREATE OR REPLACE FUNCTION top_up_wallet(
    p_user_id BIGINT,
    p_amount NUMERIC,
    p_description TEXT DEFAULT 'Wallet top-up'
)
RETURNS TABLE (
    wallet_id BIGINT,
    new_balance NUMERIC,
    reference_code VARCHAR
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_wallet_id BIGINT;
    v_new_balance NUMERIC(16,2);
    v_reference VARCHAR(100):='TOPUP-'||upper(replace(gen_random_uuid()::TEXT,'-',''));
BEGIN
    IF p_user_id IS NULL THEN
        RAISE EXCEPTION 'User is required.';
    END IF;
    IF p_amount IS NULL OR p_amount<=0 THEN
        RAISE EXCEPTION 'Top-up amount must be positive.';
    END IF;
    IF NOT EXISTS(
        SELECT 1 FROM users
        WHERE id=p_user_id AND role='spectator' AND is_active
    ) THEN
        RAISE EXCEPTION 'User % is not an active spectator.',p_user_id;
    END IF;

    UPDATE wallets
    SET balance=balance+p_amount
    WHERE user_id=p_user_id
    RETURNING id,balance INTO v_wallet_id,v_new_balance;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Wallet for user % does not exist.',p_user_id;
    END IF;

    INSERT INTO wallet_transactions
        (wallet_id,transaction_type,amount,balance_after,reference_code,description)
    VALUES
        (v_wallet_id,'top_up',p_amount,v_new_balance,v_reference,
         COALESCE(NULLIF(btrim(p_description),''),'Wallet top-up'));

    RETURN QUERY SELECT v_wallet_id,v_new_balance,v_reference;
END;
$$;


CREATE OR REPLACE FUNCTION request_cancellation(
    p_user_id BIGINT,
    p_reservation_id BIGINT,
    p_reason TEXT
)
RETURNS TABLE (
    request_id BIGINT,
    penalty_percentage NUMERIC,
    estimated_refund NUMERIC,
    request_status VARCHAR
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_reservation RECORD;
    v_penalty NUMERIC(5,2);
    v_refund NUMERIC(16,2);
    v_request_id BIGINT;
BEGIN
    IF p_reason IS NULL OR btrim(p_reason)='' THEN
        RAISE EXCEPTION 'Cancellation reason is required.';
    END IF;
    IF NOT EXISTS(
        SELECT 1 FROM users
        WHERE id=p_user_id AND role='spectator' AND is_active
    ) THEN
        RAISE EXCEPTION 'User % is not an active spectator.',p_user_id;
    END IF;

    SELECT r.id,r.user_id,r.ticket_id,r.status,r.total_amount,r.expires_at,
           m.starts_at
    INTO v_reservation
    FROM reservations r
    JOIN tickets t ON t.id=r.ticket_id
    JOIN matches m ON m.id=t.match_id
    WHERE r.id=p_reservation_id
    FOR UPDATE OF r;

    IF NOT FOUND OR v_reservation.user_id<>p_user_id THEN
        RAISE EXCEPTION 'Reservation % does not belong to user %.',p_reservation_id,p_user_id;
    END IF;
    IF v_reservation.status NOT IN ('held','paid') THEN
        RAISE EXCEPTION 'Reservation status % cannot be canceled.',v_reservation.status;
    END IF;
    IF v_reservation.status='held'
       AND v_reservation.expires_at<=CURRENT_TIMESTAMP THEN
        RAISE EXCEPTION 'Reservation % has already expired.',p_reservation_id;
    END IF;
    IF v_reservation.status='paid' AND (
        v_reservation.starts_at<=CURRENT_TIMESTAMP
        OR EXISTS(
            SELECT 1 FROM issued_tickets
            WHERE reservation_id=p_reservation_id AND status='used'
        )
    ) THEN
        RAISE EXCEPTION 'A started or used ticket cannot be canceled.';
    END IF;
    IF EXISTS(
        SELECT 1 FROM cancellation_requests
        WHERE reservation_id=p_reservation_id AND status='pending'
    ) THEN
        RAISE EXCEPTION 'A pending cancellation request already exists.';
    END IF;

    
    PERFORM release_pending_seat_change_holds(
        p_reservation_id,
        'Destination hold released because cancellation was requested'
    );

    v_penalty:=CASE
        WHEN v_reservation.status='held' THEN 0.00
        ELSE fn_get_penalty_percentage(v_reservation.ticket_id)
    END;
    v_refund:=CASE
        WHEN v_reservation.status='held' THEN 0.00
        ELSE ROUND(v_reservation.total_amount*(100-v_penalty)/100,2)
    END;

    INSERT INTO cancellation_requests
        (reservation_id,requested_by,reason,status,
         estimated_penalty_pct,estimated_refund)
    VALUES
        (p_reservation_id,p_user_id,p_reason,'pending',v_penalty,v_refund)
    RETURNING id INTO v_request_id;

    RETURN QUERY SELECT v_request_id,v_penalty,v_refund,'pending'::VARCHAR;
END;
$$;



CREATE OR REPLACE FUNCTION review_cancellation(
    p_support_user_id BIGINT,
    p_request_id BIGINT,
    p_approve BOOLEAN,
    p_review_note TEXT DEFAULT NULL
)
RETURNS TABLE (
    request_id BIGINT,
    final_request_status VARCHAR,
    reservation_status VARCHAR,
    refund_amount NUMERIC,
    penalty_amount NUMERIC
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_request RECORD;
    v_payment RECORD;
    v_penalty_pct NUMERIC(5,2):=0;
    v_penalty_amount NUMERIC(16,2):=0;
    v_refund_amount NUMERIC(16,2):=0;
    v_wallet_id BIGINT;
    v_new_balance NUMERIC(16,2);
    v_refund_ref VARCHAR(100):='REF-'||upper(replace(gen_random_uuid()::TEXT,'-',''));
    v_final_reservation_status VARCHAR(20);
BEGIN
    IF p_approve IS NULL THEN
        RAISE EXCEPTION 'Approval decision is required.';
    END IF;
    IF NOT EXISTS(
        SELECT 1 FROM users
        WHERE id=p_support_user_id AND role='support' AND is_active
    ) THEN
        RAISE EXCEPTION 'User % is not an active support user.',p_support_user_id;
    END IF;

    SELECT
        cr.id,cr.status AS request_status,cr.reservation_id,
        r.user_id,r.ticket_id,r.status AS reservation_status,
        r.quantity,r.total_amount,r.expires_at,m.starts_at
    INTO v_request
    FROM cancellation_requests cr
    JOIN reservations r ON r.id=cr.reservation_id
    JOIN tickets t ON t.id=r.ticket_id
    JOIN matches m ON m.id=t.match_id
    WHERE cr.id=p_request_id
    FOR UPDATE OF cr,r;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Cancellation request % does not exist.',p_request_id;
    END IF;
    IF v_request.request_status<>'pending' THEN
        RAISE EXCEPTION 'Cancellation request is already %.',v_request.request_status;
    END IF;

    IF NOT p_approve THEN
        UPDATE cancellation_requests
        SET status='rejected',reviewed_by=p_support_user_id,
            review_note=p_review_note,reviewed_at=CURRENT_TIMESTAMP
        WHERE id=p_request_id;

        RETURN QUERY
        SELECT p_request_id,'rejected'::VARCHAR,
               v_request.reservation_status::VARCHAR,0::NUMERIC,0::NUMERIC;
        RETURN;
    END IF;

    PERFORM release_pending_seat_change_holds(
        v_request.reservation_id,
        'Destination hold released because cancellation was approved'
    );

    IF v_request.reservation_status='held' THEN
        UPDATE tickets
        SET held_quantity=held_quantity-v_request.quantity
        WHERE id=v_request.ticket_id
          AND held_quantity>=v_request.quantity;

        IF NOT FOUND THEN
            RAISE EXCEPTION 'Ticket held counter is inconsistent for reservation %.',v_request.reservation_id;
        END IF;

        v_final_reservation_status:='canceled';

    ELSIF v_request.reservation_status='paid' THEN
        IF v_request.starts_at<=CURRENT_TIMESTAMP OR EXISTS(
            SELECT 1 FROM issued_tickets
            WHERE reservation_id=v_request.reservation_id AND status='used'
        ) THEN
            RAISE EXCEPTION 'A started or used ticket cannot be canceled/refunded.';
        END IF;

        SELECT p.id,p.amount
        INTO v_payment
        FROM payments p
        WHERE p.reservation_id=v_request.reservation_id
          AND p.status='successful'
        FOR UPDATE;

        IF NOT FOUND THEN
            RAISE EXCEPTION 'Successful payment for reservation % was not found.',v_request.reservation_id;
        END IF;
        IF EXISTS(SELECT 1 FROM refunds WHERE payment_id=v_payment.id) THEN
            RAISE EXCEPTION 'Payment % already has a refund.',v_payment.id;
        END IF;
        IF (
            SELECT COUNT(*)
            FROM issued_tickets
            WHERE reservation_id=v_request.reservation_id AND status='active'
        )<>v_request.quantity THEN
            RAISE EXCEPTION 'Reservation % does not have exactly % active issued tickets.',
                v_request.reservation_id,v_request.quantity;
        END IF;

        v_penalty_pct:=fn_get_penalty_percentage(v_request.ticket_id);
        v_penalty_amount:=ROUND(v_payment.amount*v_penalty_pct/100,2);
        v_refund_amount:=v_payment.amount-v_penalty_amount;

        UPDATE tickets
        SET sold_quantity=sold_quantity-v_request.quantity
        WHERE id=v_request.ticket_id
          AND sold_quantity>=v_request.quantity;

        IF NOT FOUND THEN
            RAISE EXCEPTION 'Ticket sold counter is inconsistent for reservation %.',v_request.reservation_id;
        END IF;

        UPDATE issued_tickets
        SET status='canceled',used_at=NULL
        WHERE reservation_id=v_request.reservation_id
          AND status='active';

        SELECT id
        INTO v_wallet_id
        FROM wallets
        WHERE user_id=v_request.user_id
        FOR UPDATE;

        IF NOT FOUND THEN
            RAISE EXCEPTION 'Wallet for user % does not exist.',v_request.user_id;
        END IF;

        UPDATE wallets
        SET balance=balance+v_refund_amount
        WHERE id=v_wallet_id
        RETURNING balance INTO v_new_balance;

        INSERT INTO refunds
            (cancellation_request_id,payment_id,wallet_id,amount,penalty_amount,
             status,transaction_ref,created_at,completed_at)
        VALUES
            (p_request_id,v_payment.id,v_wallet_id,v_refund_amount,
             v_penalty_amount,'completed',v_refund_ref,
             CURRENT_TIMESTAMP,CURRENT_TIMESTAMP);

        IF v_refund_amount>0 THEN
            INSERT INTO wallet_transactions
                (wallet_id,payment_id,transaction_type,amount,balance_after,
                 reference_code,description)
            VALUES
                (v_wallet_id,v_payment.id,'refund',v_refund_amount,v_new_balance,
                 'WT-'||v_refund_ref,'Approved ticket cancellation');
        END IF;

        v_final_reservation_status:='refunded';
    ELSE
        RAISE EXCEPTION 'Reservation status % cannot be approved for cancellation.',
            v_request.reservation_status;
    END IF;

    UPDATE reservations
    SET status=v_final_reservation_status,
        canceled_at=CURRENT_TIMESTAMP,
        canceled_by=p_support_user_id,
        cancellation_reason=COALESCE(NULLIF(btrim(p_review_note),''),'Cancellation approved')
    WHERE id=v_request.reservation_id;

    UPDATE cancellation_requests
    SET status='processed',
        reviewed_by=p_support_user_id,
        review_note=p_review_note,
        reviewed_at=CURRENT_TIMESTAMP,
        estimated_penalty_pct=v_penalty_pct,
        estimated_refund=v_refund_amount
    WHERE id=p_request_id;

    RETURN QUERY
    SELECT p_request_id,'processed'::VARCHAR,v_final_reservation_status,
           v_refund_amount,v_penalty_amount;
END;
$$;



CREATE OR REPLACE FUNCTION request_seat_change(
    p_user_id BIGINT,
    p_reservation_id BIGINT,
    p_new_ticket_id BIGINT
)
RETURNS BIGINT
LANGUAGE plpgsql
AS $$
DECLARE
    v_reservation RECORD;
    v_old_ticket RECORD;
    v_new_ticket RECORD;
    v_request_id BIGINT;
    v_hold_expires TIMESTAMPTZ;
BEGIN
    IF p_user_id IS NULL OR p_reservation_id IS NULL OR p_new_ticket_id IS NULL THEN
        RAISE EXCEPTION 'User, reservation and destination ticket are required.';
    END IF;
    IF NOT EXISTS(
        SELECT 1 FROM users
        WHERE id=p_user_id AND role='spectator' AND is_active
    ) THEN
        RAISE EXCEPTION 'User % is not an active spectator.',p_user_id;
    END IF;

    SELECT r.id,r.user_id,r.ticket_id,r.status,r.quantity,r.unit_price,
           r.expires_at,m.starts_at,m.status AS match_status,
           m.is_active AS match_active,v.is_active AS venue_active,
           o.is_active AS organizer_active,st.is_active AS sport_active,
           ht.is_active AS home_team_active,at.is_active AS away_team_active
    INTO v_reservation
    FROM reservations r
    JOIN tickets ot ON ot.id=r.ticket_id
    JOIN matches m ON m.id=ot.match_id
    JOIN sport_types st ON st.id=m.sport_type_id
    JOIN teams ht ON ht.id=m.home_team_id
    JOIN teams at ON at.id=m.away_team_id
    JOIN venues v ON v.id=m.venue_id
    JOIN organizers o ON o.id=m.organizer_id
    WHERE r.id=p_reservation_id
    FOR UPDATE OF r;

    IF NOT FOUND OR v_reservation.user_id<>p_user_id THEN
        RAISE EXCEPTION 'Reservation % does not belong to user %.',p_reservation_id,p_user_id;
    END IF;
    IF v_reservation.status NOT IN ('held','paid') THEN
        RAISE EXCEPTION 'Seat/section change is not allowed for status %.',v_reservation.status;
    END IF;
    IF v_reservation.status='held'
       AND v_reservation.expires_at<=CURRENT_TIMESTAMP THEN
        RAISE EXCEPTION 'Reservation % has already expired.',p_reservation_id;
    END IF;
    IF v_reservation.match_status NOT IN ('scheduled','postponed')
       OR NOT v_reservation.match_active
       OR NOT v_reservation.venue_active
       OR NOT v_reservation.organizer_active
       OR NOT v_reservation.sport_active
       OR NOT v_reservation.home_team_active
       OR NOT v_reservation.away_team_active
       OR v_reservation.starts_at<=CURRENT_TIMESTAMP THEN
        RAISE EXCEPTION 'The match is not eligible for a seat/section change.';
    END IF;
    IF v_reservation.status='paid' AND EXISTS(
        SELECT 1 FROM issued_tickets
        WHERE reservation_id=p_reservation_id AND status='used'
    ) THEN
        RAISE EXCEPTION 'A used ticket cannot change seats.';
    END IF;
    IF v_reservation.ticket_id=p_new_ticket_id THEN
        RAISE EXCEPTION 'Destination ticket must differ from the current ticket.';
    END IF;
    IF EXISTS(
        SELECT 1 FROM seat_change_requests
        WHERE reservation_id=p_reservation_id AND status='pending'
    ) THEN
        RAISE EXCEPTION 'A pending seat-change request already exists.';
    END IF;
    IF EXISTS(
        SELECT 1 FROM cancellation_requests
        WHERE reservation_id=p_reservation_id AND status='pending'
    ) THEN
        RAISE EXCEPTION 'A pending cancellation request blocks seat/section changes.';
    END IF;

    
    PERFORM id
    FROM tickets
    WHERE id IN (v_reservation.ticket_id,p_new_ticket_id)
    ORDER BY id
    FOR UPDATE;

    SELECT id,match_id,price,is_numbered,is_active
    INTO v_old_ticket
    FROM tickets
    WHERE id=v_reservation.ticket_id;

    SELECT t.id,t.match_id,t.price,t.is_numbered,t.is_active,t.available_quantity,
           t.sale_starts_at,t.sale_ends_at,tc.is_active AS category_active
    INTO v_new_ticket
    FROM tickets t
    JOIN ticket_categories tc ON tc.id=t.ticket_category_id
    WHERE t.id=p_new_ticket_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Destination ticket % does not exist.',p_new_ticket_id;
    END IF;
    IF v_old_ticket.match_id<>v_new_ticket.match_id THEN
        RAISE EXCEPTION 'Destination must belong to the same match.';
    END IF;
    IF v_new_ticket.price<>v_reservation.unit_price THEN
        RAISE EXCEPTION 'Destination price % differs from reservation price %. Use cancellation/rebooking for a priced upgrade or downgrade.',
            v_new_ticket.price,v_reservation.unit_price;
    END IF;
    IF v_new_ticket.is_numbered AND v_reservation.quantity<>1 THEN
        RAISE EXCEPTION 'A numbered destination seat requires reservation quantity 1.';
    END IF;
    IF NOT v_new_ticket.is_active OR NOT v_new_ticket.category_active
       OR v_new_ticket.available_quantity<v_reservation.quantity THEN
        RAISE EXCEPTION 'Destination ticket is unavailable.';
    END IF;
    IF v_new_ticket.sale_starts_at IS NOT NULL
       AND CURRENT_TIMESTAMP<v_new_ticket.sale_starts_at THEN
        RAISE EXCEPTION 'Destination ticket sale has not started.';
    END IF;
    IF v_new_ticket.sale_ends_at IS NOT NULL
       AND CURRENT_TIMESTAMP>=v_new_ticket.sale_ends_at THEN
        RAISE EXCEPTION 'Destination ticket sale has ended.';
    END IF;

    v_hold_expires:=LEAST(
        CURRENT_TIMESTAMP+INTERVAL '30 minutes',
        v_reservation.starts_at-INTERVAL '1 second',
        COALESCE(v_new_ticket.sale_ends_at,'infinity'::TIMESTAMPTZ),
        CASE WHEN v_reservation.status='held'
             THEN v_reservation.expires_at
             ELSE v_reservation.starts_at-INTERVAL '1 second'
        END
    );

    IF v_hold_expires<=CURRENT_TIMESTAMP THEN
        RAISE EXCEPTION 'There is not enough time to create a destination hold.';
    END IF;

    UPDATE tickets
    SET change_held_quantity=change_held_quantity+v_reservation.quantity
    WHERE id=p_new_ticket_id
      AND available_quantity>=v_reservation.quantity;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Destination ticket is no longer available.';
    END IF;

    INSERT INTO seat_change_requests
        (reservation_id,requested_by,old_ticket_id,requested_ticket_id,
         quantity,old_unit_price,new_unit_price,target_hold_expires_at,status)
    VALUES
        (p_reservation_id,p_user_id,v_reservation.ticket_id,p_new_ticket_id,
         v_reservation.quantity,v_reservation.unit_price,v_new_ticket.price,
         v_hold_expires,'pending')
    RETURNING id INTO v_request_id;

    RETURN v_request_id;
END;
$$;


CREATE OR REPLACE FUNCTION review_seat_change(
    p_support_user_id BIGINT,
    p_request_id BIGINT,
    p_approve BOOLEAN,
    p_review_note TEXT DEFAULT NULL
)
RETURNS TABLE (
    request_id BIGINT,
    request_status VARCHAR,
    reservation_id BIGINT,
    active_ticket_id BIGINT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_request RECORD;
    v_destination_change_hold INTEGER;
BEGIN
    IF p_approve IS NULL THEN
        RAISE EXCEPTION 'Approval decision is required.';
    END IF;
    IF NOT EXISTS(
        SELECT 1 FROM users
        WHERE id=p_support_user_id AND role='support' AND is_active
    ) THEN
        RAISE EXCEPTION 'User % is not an active support user.',p_support_user_id;
    END IF;

    SELECT
        scr.id,scr.status,scr.reservation_id,scr.old_ticket_id,
        scr.requested_ticket_id,scr.quantity,scr.target_hold_expires_at,
        r.ticket_id AS current_ticket_id,r.status AS reservation_status,r.unit_price,
        r.expires_at,m.starts_at,m.status AS match_status,m.is_active AS match_active,
        v.is_active AS venue_active,o.is_active AS organizer_active,
        st.is_active AS sport_active,ht.is_active AS home_team_active,
        at.is_active AS away_team_active,
        ot.match_id AS old_match_id,nt.match_id AS destination_match_id,
        nt.is_active AS destination_active,nt.price AS destination_price,
        ntc.is_active AS destination_category_active,
        scr.new_unit_price AS destination_price_snapshot
    INTO v_request
    FROM seat_change_requests scr
    JOIN reservations r ON r.id=scr.reservation_id
    JOIN tickets ot ON ot.id=scr.old_ticket_id
    JOIN tickets nt ON nt.id=scr.requested_ticket_id
    JOIN matches m ON m.id=ot.match_id
    JOIN sport_types st ON st.id=m.sport_type_id
    JOIN teams ht ON ht.id=m.home_team_id
    JOIN teams at ON at.id=m.away_team_id
    JOIN venues v ON v.id=m.venue_id
    JOIN organizers o ON o.id=m.organizer_id
    JOIN ticket_categories ntc ON ntc.id=nt.ticket_category_id
    WHERE scr.id=p_request_id
    FOR UPDATE OF scr,r;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Seat-change request % does not exist.',p_request_id;
    END IF;
    IF v_request.status<>'pending' THEN
        RAISE EXCEPTION 'Seat-change request is already %.',v_request.status;
    END IF;
    IF v_request.current_ticket_id<>v_request.old_ticket_id THEN
        RAISE EXCEPTION 'Reservation ticket changed after this request was created.';
    END IF;

    PERFORM id
    FROM tickets
    WHERE id IN (v_request.old_ticket_id,v_request.requested_ticket_id)
    ORDER BY id
    FOR UPDATE;

    SELECT change_held_quantity
    INTO v_destination_change_hold
    FROM tickets
    WHERE id=v_request.requested_ticket_id;

    IF v_destination_change_hold<v_request.quantity THEN
        RAISE EXCEPTION 'Destination-hold counter is inconsistent for request %.',p_request_id;
    END IF;

    IF v_request.target_hold_expires_at<=CURRENT_TIMESTAMP
       OR v_request.match_status NOT IN ('scheduled','postponed')
       OR NOT v_request.match_active
       OR NOT v_request.venue_active
       OR NOT v_request.organizer_active
       OR NOT v_request.sport_active
       OR NOT v_request.home_team_active
       OR NOT v_request.away_team_active
       OR NOT v_request.destination_active
       OR NOT v_request.destination_category_active
       OR v_request.old_match_id<>v_request.destination_match_id
       OR v_request.destination_price<>v_request.destination_price_snapshot
       OR v_request.destination_price<>v_request.unit_price
       OR v_request.starts_at<=CURRENT_TIMESTAMP THEN

        UPDATE tickets
        SET change_held_quantity=change_held_quantity-v_request.quantity
        WHERE id=v_request.requested_ticket_id;

        IF v_request.reservation_status='held'
           AND (v_request.expires_at<=CURRENT_TIMESTAMP
                OR v_request.starts_at<=CURRENT_TIMESTAMP) THEN
            UPDATE tickets
            SET held_quantity=held_quantity-v_request.quantity
            WHERE id=v_request.old_ticket_id
              AND held_quantity>=v_request.quantity;

            IF NOT FOUND THEN
                RAISE EXCEPTION 'Old-ticket held counter is inconsistent.';
            END IF;

            UPDATE reservations
            SET status='expired',canceled_at=CURRENT_TIMESTAMP,canceled_by=NULL,
                cancellation_reason='Reservation became ineligible during seat-change review'
            WHERE id=v_request.reservation_id;
        END IF;

        UPDATE seat_change_requests
        SET status='expired',reviewed_by=NULL,reviewed_at=CURRENT_TIMESTAMP,
            review_note='Destination hold expired or destination/match became ineligible'
        WHERE id=p_request_id;

        RETURN QUERY
        SELECT p_request_id,'expired'::VARCHAR,
               v_request.reservation_id,v_request.old_ticket_id;
        RETURN;
    END IF;

    IF v_request.reservation_status='held'
       AND v_request.expires_at<=CURRENT_TIMESTAMP THEN
        UPDATE tickets
        SET change_held_quantity=change_held_quantity-v_request.quantity
        WHERE id=v_request.requested_ticket_id;

        UPDATE tickets
        SET held_quantity=held_quantity-v_request.quantity
        WHERE id=v_request.old_ticket_id
          AND held_quantity>=v_request.quantity;

        IF NOT FOUND THEN
            RAISE EXCEPTION 'Old-ticket held counter is inconsistent.';
        END IF;

        UPDATE reservations
        SET status='expired',canceled_at=CURRENT_TIMESTAMP,canceled_by=NULL,
            cancellation_reason='Reservation expired during seat-change review'
        WHERE id=v_request.reservation_id;

        UPDATE seat_change_requests
        SET status='expired',reviewed_by=NULL,reviewed_at=CURRENT_TIMESTAMP,
            review_note='Reservation expired before seat-change review'
        WHERE id=p_request_id;

        RETURN QUERY
        SELECT p_request_id,'expired'::VARCHAR,
               v_request.reservation_id,v_request.old_ticket_id;
        RETURN;
    END IF;

    IF v_request.reservation_status='paid' AND EXISTS(
        SELECT 1
        FROM issued_tickets AS it
        WHERE it.reservation_id=v_request.reservation_id
          AND it.status='used'
    ) THEN
        RAISE EXCEPTION 'A used ticket cannot change seats.';
    END IF;

    IF NOT p_approve THEN
        UPDATE tickets
        SET change_held_quantity=change_held_quantity-v_request.quantity
        WHERE id=v_request.requested_ticket_id;

        UPDATE seat_change_requests
        SET status='rejected',reviewed_by=p_support_user_id,
            review_note=p_review_note,reviewed_at=CURRENT_TIMESTAMP
        WHERE id=p_request_id;

        RETURN QUERY
        SELECT p_request_id,'rejected'::VARCHAR,
               v_request.reservation_id,v_request.old_ticket_id;
        RETURN;
    END IF;

    IF v_request.reservation_status='held' THEN
        UPDATE tickets
        SET held_quantity=held_quantity-v_request.quantity
        WHERE id=v_request.old_ticket_id
          AND held_quantity>=v_request.quantity;

        IF NOT FOUND THEN
            RAISE EXCEPTION 'Old-ticket held counter is inconsistent.';
        END IF;

        UPDATE tickets
        SET change_held_quantity=change_held_quantity-v_request.quantity,
            held_quantity=held_quantity+v_request.quantity
        WHERE id=v_request.requested_ticket_id
          AND change_held_quantity>=v_request.quantity;

        IF NOT FOUND THEN
            RAISE EXCEPTION 'Destination hold is inconsistent.';
        END IF;

    ELSIF v_request.reservation_status='paid' THEN
        UPDATE tickets
        SET sold_quantity=sold_quantity-v_request.quantity
        WHERE id=v_request.old_ticket_id
          AND sold_quantity>=v_request.quantity;

        IF NOT FOUND THEN
            RAISE EXCEPTION 'Old-ticket sold counter is inconsistent.';
        END IF;

        UPDATE tickets
        SET change_held_quantity=change_held_quantity-v_request.quantity,
            sold_quantity=sold_quantity+v_request.quantity
        WHERE id=v_request.requested_ticket_id
          AND change_held_quantity>=v_request.quantity;

        IF NOT FOUND THEN
            RAISE EXCEPTION 'Destination hold is inconsistent.';
        END IF;
    ELSE
        RAISE EXCEPTION 'Reservation status % cannot change seat/section.',
            v_request.reservation_status;
    END IF;

    UPDATE reservations
    SET ticket_id=v_request.requested_ticket_id
    WHERE id=v_request.reservation_id;

    UPDATE seat_change_requests
    SET status='processed',reviewed_by=p_support_user_id,
        review_note=p_review_note,reviewed_at=CURRENT_TIMESTAMP
    WHERE id=p_request_id;

    RETURN QUERY
    SELECT p_request_id,'processed'::VARCHAR,
           v_request.reservation_id,v_request.requested_ticket_id;
END;
$$;




CREATE OR REPLACE FUNCTION deactivate_user(
    p_support_user_id BIGINT,
    p_target_user_id BIGINT,
    p_reason TEXT DEFAULT 'Account deactivated by support'
)
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    rec RECORD;
    v_released INTEGER:=0;
BEGIN
    IF NOT EXISTS(
        SELECT 1 FROM users
        WHERE id=p_support_user_id AND role='support' AND is_active
    ) THEN
        RAISE EXCEPTION 'User % is not an active support user.',p_support_user_id;
    END IF;
    IF p_target_user_id=p_support_user_id THEN
        RAISE EXCEPTION 'A support user cannot deactivate the same account through this workflow.';
    END IF;
    IF NOT EXISTS(
        SELECT 1 FROM users
        WHERE id=p_target_user_id AND role='spectator'
    ) THEN
        RAISE EXCEPTION 'Only spectator accounts can be deactivated through this workflow.';
    END IF;

    UPDATE users
    SET is_active=FALSE
    WHERE id=p_target_user_id AND role='spectator';

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Target spectator % does not exist.',p_target_user_id;
    END IF;

    FOR rec IN
        SELECT id,ticket_id,quantity
        FROM reservations
        WHERE user_id=p_target_user_id
          AND status='held'
        ORDER BY id
        FOR UPDATE
    LOOP
        PERFORM release_pending_seat_change_holds(
            rec.id,
            'Destination hold released because account was deactivated'
        );

        UPDATE tickets
        SET held_quantity=held_quantity-rec.quantity
        WHERE id=rec.ticket_id
          AND held_quantity>=rec.quantity;

        IF NOT FOUND THEN
            RAISE EXCEPTION 'Ticket held counter is inconsistent for reservation %.',rec.id;
        END IF;

        UPDATE reservations
        SET status='canceled',
            canceled_at=CURRENT_TIMESTAMP,
            canceled_by=p_support_user_id,
            cancellation_reason=COALESCE(NULLIF(btrim(p_reason),''),'Account deactivated by support')
        WHERE id=rec.id;

        v_released:=v_released+1;
    END LOOP;

    
    
    FOR rec IN
        SELECT id
        FROM reservations
        WHERE user_id=p_target_user_id
          AND status='paid'
    LOOP
        PERFORM release_pending_seat_change_holds(
            rec.id,
            'Destination hold released because account was deactivated'
        );
    END LOOP;

    UPDATE cancellation_requests cr
    SET status='rejected',reviewed_by=p_support_user_id,
        reviewed_at=CURRENT_TIMESTAMP,
        review_note='Request closed because account was deactivated'
    FROM reservations r
    WHERE cr.reservation_id=r.id
      AND r.user_id=p_target_user_id
      AND cr.status='pending';

    RETURN v_released;
END;
$$;

COMMIT;
