
BEGIN;

CREATE OR REPLACE FUNCTION sp_get_purchased_tickets_by_contact(p_contact TEXT)
RETURNS TABLE (
    payment_id          BIGINT,
    paid_at             TIMESTAMPTZ,
    reservation_id      BIGINT,
    reservation_status  VARCHAR,
    ticket_id           BIGINT,
    quantity            INTEGER,
    unit_price          NUMERIC,
    total_amount        NUMERIC,
    sport_name          VARCHAR,
    home_team           VARCHAR,
    away_team           VARCHAR,
    venue_name          VARCHAR,
    category_name       VARCHAR,
    section_code        VARCHAR,
    row_code            VARCHAR,
    seat_code           VARCHAR,
    match_starts_at     TIMESTAMPTZ
)
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
    IF p_contact IS NULL OR btrim(p_contact) = '' THEN
        RAISE EXCEPTION 'Email or phone is required.';
    END IF;

    RETURN QUERY
    SELECT
        vpt.payment_id,
        vpt.paid_at,
        vpt.reservation_id,
        vpt.reservation_status,
        vpt.ticket_id,
        vpt.quantity,
        vpt.unit_price,
        vpt.total_amount,
        vpt.sport_name,
        vpt.home_team,
        vpt.away_team,
        vpt.venue_name,
        vpt.category_name,
        vpt.section_code,
        vpt.row_code,
        vpt.seat_code,
        vpt.starts_at
    FROM v_purchased_tickets vpt
    WHERE lower(vpt.email::TEXT) = lower(btrim(p_contact))
       OR vpt.phone = btrim(p_contact)
    ORDER BY vpt.paid_at DESC, vpt.payment_id DESC;
END;
$$;

CREATE OR REPLACE FUNCTION sp_get_users_canceled_by_support(p_support_contact TEXT)
RETURNS TABLE (
    user_id BIGINT,first_name VARCHAR,last_name VARCHAR,email TEXT,phone VARCHAR,
    canceled_reservation_count BIGINT,canceled_ticket_count BIGINT,last_cancellation_at TIMESTAMPTZ
)
LANGUAGE plpgsql STABLE AS $$
DECLARE v_support_id BIGINT;
BEGIN
    IF p_support_contact IS NULL OR btrim(p_support_contact)='' THEN
        RAISE EXCEPTION 'Support email or phone is required.';
    END IF;
    SELECT u.id INTO v_support_id FROM users u
    WHERE u.role='support' AND u.is_active
      AND (lower(u.email::TEXT)=lower(btrim(p_support_contact)) OR u.phone=btrim(p_support_contact));
    IF v_support_id IS NULL THEN RAISE EXCEPTION 'Active support user with contact % was not found.',p_support_contact; END IF;
    RETURN QUERY
    WITH c AS (
        SELECT u.id AS c_user_id,u.first_name AS c_first_name,u.last_name AS c_last_name,
               u.email::TEXT AS c_email,u.phone AS c_phone,COUNT(r.id) AS c_res_count,
               SUM(r.quantity)::BIGINT AS c_ticket_count,MAX(r.canceled_at) AS c_last_at
        FROM reservations r JOIN users u ON u.id=r.user_id
        WHERE r.canceled_by=v_support_id AND r.status IN ('canceled','refunded')
        GROUP BY u.id,u.first_name,u.last_name,u.email,u.phone
    )
    SELECT c.c_user_id,c.c_first_name,c.c_last_name,c.c_email,c.c_phone,
           c.c_res_count,c.c_ticket_count,c.c_last_at
    FROM c ORDER BY c.c_ticket_count DESC,c.c_last_at DESC,c.c_user_id;
END; $$;

CREATE OR REPLACE FUNCTION sp_get_purchased_tickets_by_city(p_city_name TEXT)
RETURNS TABLE (
    payment_id      BIGINT,
    paid_at         TIMESTAMPTZ,
    buyer_name      TEXT,
    buyer_email     TEXT,
    buyer_phone     VARCHAR,
    ticket_id       BIGINT,
    quantity        INTEGER,
    sport_name      VARCHAR,
    home_team       VARCHAR,
    away_team       VARCHAR,
    venue_name      VARCHAR,
    city_name       VARCHAR,
    province_name   VARCHAR,
    match_starts_at TIMESTAMPTZ
)
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
    IF p_city_name IS NULL OR btrim(p_city_name) = '' THEN
        RAISE EXCEPTION 'City name is required.';
    END IF;

    RETURN QUERY
    SELECT
        vpt.payment_id,
        vpt.paid_at,
        vpt.first_name || ' ' || vpt.last_name,
        vpt.email::TEXT,
        vpt.phone,
        vpt.ticket_id,
        vpt.quantity,
        vpt.sport_name,
        vpt.home_team,
        vpt.away_team,
        vpt.venue_name,
        vpt.venue_city,
        vpt.venue_province,
        vpt.starts_at
    FROM v_purchased_tickets vpt
    WHERE lower(vpt.venue_city) = lower(btrim(p_city_name))
    ORDER BY vpt.paid_at DESC, vpt.payment_id DESC;
END;
$$;

CREATE OR REPLACE FUNCTION sp_search_tickets(p_phrase TEXT)
RETURNS TABLE (
    ticket_id BIGINT,
    sport_name VARCHAR,
    home_team VARCHAR,
    away_team VARCHAR,
    tournament_name VARCHAR,
    venue_name VARCHAR,
    city_name VARCHAR,
    category_name VARCHAR,
    section_code VARCHAR,
    row_code VARCHAR,
    seat_code VARCHAR,
    price NUMERIC,
    available_quantity INTEGER,
    match_starts_at TIMESTAMPTZ,
    matched_buyer_name TEXT
)
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_pattern TEXT;
BEGIN
    IF p_phrase IS NULL OR btrim(p_phrase)='' THEN
        RAISE EXCEPTION 'Search phrase is required.';
    END IF;

    v_pattern := '%' || lower(btrim(p_phrase)) || '%';

    RETURN QUERY
    SELECT
        t.id,
        st.name,
        ht.name,
        at.name,
        m.tournament_name,
        v.name,
        c.name,
        tc.name,
        t.section_code,
        t.row_code,
        t.seat_code,
        t.price,
        t.available_quantity,
        m.starts_at,
        buyer.matched_names
    FROM tickets t
    JOIN matches m ON m.id=t.match_id
    JOIN sport_types st ON st.id=m.sport_type_id
    JOIN teams ht ON ht.id=m.home_team_id
    JOIN teams at ON at.id=m.away_team_id
    JOIN venues v ON v.id=m.venue_id
    JOIN cities c ON c.id=v.city_id
    JOIN ticket_categories tc ON tc.id=t.ticket_category_id
    LEFT JOIN LATERAL (
        SELECT string_agg(
                   DISTINCT (u.first_name||' '||u.last_name),
                   ', ' ORDER BY (u.first_name||' '||u.last_name)
               ) AS matched_names
        FROM reservations r
        JOIN users u ON u.id=r.user_id
        WHERE r.ticket_id=t.id
          AND lower(u.first_name||' '||u.last_name) LIKE v_pattern
    ) buyer ON TRUE
    WHERE t.is_active
      AND m.is_active
      AND v.is_active
      AND m.status IN ('scheduled','postponed')
      AND m.starts_at>CURRENT_TIMESTAMP
      AND t.available_quantity>0
      AND (t.sale_starts_at IS NULL OR t.sale_starts_at<=CURRENT_TIMESTAMP)
      AND (t.sale_ends_at IS NULL OR t.sale_ends_at>CURRENT_TIMESTAMP)
      AND (
          lower(st.name) LIKE v_pattern
          OR lower(st.code) LIKE v_pattern
          OR lower(ht.name) LIKE v_pattern
          OR lower(at.name) LIKE v_pattern
          OR lower(v.name) LIKE v_pattern
          OR lower(c.name) LIKE v_pattern
          OR lower(m.tournament_name) LIKE v_pattern
          OR lower(tc.name) LIKE v_pattern
          OR lower(tc.code) LIKE v_pattern
          OR lower(t.section_code) LIKE v_pattern
          OR EXISTS (
              SELECT 1
              FROM ticket_amenities ta
              JOIN amenities a ON a.id=ta.amenity_id
              WHERE ta.ticket_id=t.id
                AND lower(a.name) LIKE v_pattern
          )
          OR buyer.matched_names IS NOT NULL
      )
    ORDER BY m.starts_at,t.price,t.id;
END;
$$;

CREATE OR REPLACE FUNCTION sp_get_same_city_users(p_contact TEXT)
RETURNS TABLE (
    user_id       BIGINT,
    first_name    VARCHAR,
    last_name     VARCHAR,
    email         TEXT,
    phone         VARCHAR,
    role          VARCHAR,
    city_name     VARCHAR,
    province_name VARCHAR
)
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_user_id BIGINT;
    v_city_id BIGINT;
BEGIN
    IF p_contact IS NULL OR btrim(p_contact) = '' THEN
        RAISE EXCEPTION 'Email or phone is required.';
    END IF;

    SELECT u.id, u.city_id
    INTO v_user_id, v_city_id
    FROM users u
    WHERE lower(u.email::TEXT) = lower(btrim(p_contact))
       OR u.phone = btrim(p_contact);

    IF v_user_id IS NULL THEN
        RAISE EXCEPTION 'User with contact % was not found.', p_contact;
    END IF;

    IF v_city_id IS NULL THEN
        RETURN;
    END IF;

    RETURN QUERY
    SELECT
        u.id,
        u.first_name,
        u.last_name,
        u.email::TEXT,
        u.phone,
        u.role,
        c.name,
        p.name
    FROM users u
    JOIN cities c ON c.id = u.city_id
    JOIN provinces p ON p.id = c.province_id
    WHERE u.city_id = v_city_id
      AND u.id <> v_user_id
      AND u.is_active
    ORDER BY u.last_name, u.first_name, u.id;
END;
$$;

CREATE OR REPLACE FUNCTION sp_top_buyers_since(p_from TIMESTAMPTZ,p_limit INTEGER)
RETURNS TABLE (
    user_id BIGINT,first_name VARCHAR,last_name VARCHAR,email TEXT,phone VARCHAR,
    purchase_count BIGINT,ticket_count BIGINT,total_spent NUMERIC,latest_purchase_at TIMESTAMPTZ
)
LANGUAGE plpgsql STABLE AS $$
BEGIN
    IF p_from IS NULL THEN RAISE EXCEPTION 'Start date is required.'; END IF;
    IF p_limit IS NULL OR p_limit<1 OR p_limit>100 THEN RAISE EXCEPTION 'p_limit must be between 1 and 100.'; END IF;
    RETURN QUERY
    WITH bt AS (
        SELECT u.id AS b_user_id,u.first_name AS b_first_name,u.last_name AS b_last_name,
               u.email::TEXT AS b_email,u.phone AS b_phone,COUNT(DISTINCT r.id) AS b_purchase_count,
               SUM(r.quantity)::BIGINT AS b_ticket_count,SUM(r.total_amount) AS b_total_spent,
               MAX(p.paid_at) AS b_latest_at
        FROM reservations r JOIN users u ON u.id=r.user_id
        JOIN payments p ON p.reservation_id=r.id AND p.status='successful'
        WHERE p.paid_at>=p_from
        GROUP BY u.id,u.first_name,u.last_name,u.email,u.phone
    )
    SELECT bt.b_user_id,bt.b_first_name,bt.b_last_name,bt.b_email,bt.b_phone,
           bt.b_purchase_count,bt.b_ticket_count,bt.b_total_spent,bt.b_latest_at
    FROM bt ORDER BY bt.b_ticket_count DESC,bt.b_total_spent DESC,bt.b_latest_at DESC,bt.b_user_id
    LIMIT p_limit;
END; $$;

CREATE OR REPLACE FUNCTION sp_get_canceled_tickets_by_sport(p_sport TEXT)
RETURNS TABLE (
    reservation_id   BIGINT,
    canceled_at      TIMESTAMPTZ,
    reservation_status VARCHAR,
    user_id          BIGINT,
    buyer_name       TEXT,
    ticket_id        BIGINT,
    quantity         INTEGER,
    sport_name       VARCHAR,
    home_team        VARCHAR,
    away_team        VARCHAR,
    venue_name       VARCHAR,
    category_name    VARCHAR,
    match_starts_at  TIMESTAMPTZ,
    cancellation_reason TEXT
)
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
    IF p_sport IS NULL OR btrim(p_sport) = '' THEN
        RAISE EXCEPTION 'Sport type is required.';
    END IF;

    RETURN QUERY
    SELECT
        r.id,
        r.canceled_at,
        r.status,
        u.id,
        u.first_name || ' ' || u.last_name,
        vc.ticket_id,
        r.quantity,
        vc.sport_name,
        vc.home_team,
        vc.away_team,
        vc.venue_name,
        vc.category_name,
        vc.starts_at,
        r.cancellation_reason
    FROM reservations r
    JOIN users u ON u.id = r.user_id
    JOIN v_ticket_catalog vc ON vc.ticket_id = r.ticket_id
    WHERE r.status IN ('canceled', 'refunded')
      AND (vc.sport_name ILIKE btrim(p_sport) OR vc.sport_code ILIKE btrim(p_sport))
    ORDER BY r.canceled_at DESC NULLS LAST, r.id DESC;
END;
$$;

CREATE OR REPLACE FUNCTION sp_top_reporters_by_subject(p_subject TEXT)
RETURNS TABLE (
    user_id       BIGINT,
    first_name    VARCHAR,
    last_name     VARCHAR,
    email         TEXT,
    phone         VARCHAR,
    report_count  BIGINT,
    latest_report TIMESTAMPTZ
)
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
    IF p_subject IS NULL OR btrim(p_subject) = '' THEN
        RAISE EXCEPTION 'Report subject/category is required.';
    END IF;

    RETURN QUERY
    WITH reporter_counts AS (
        SELECT
            u.id,
            u.first_name,
            u.last_name,
            u.email,
            u.phone,
            COUNT(*) AS report_count,
            MAX(r.created_at) AS latest_report
        FROM reports r
        JOIN report_categories rc ON rc.id = r.category_id
        JOIN users u ON u.id = r.reporter_id
        WHERE r.subject ILIKE '%' || btrim(p_subject) || '%'
           OR rc.name ILIKE '%' || btrim(p_subject) || '%'
           OR rc.code ILIKE '%' || btrim(p_subject) || '%'
        GROUP BY u.id, u.first_name, u.last_name, u.email, u.phone
    ), ranked AS (
        SELECT rcnt.*, DENSE_RANK() OVER (ORDER BY rcnt.report_count DESC) AS reporter_rank
        FROM reporter_counts rcnt
    )
    SELECT
        ranked.id,
        ranked.first_name,
        ranked.last_name,
        ranked.email::TEXT,
        ranked.phone,
        ranked.report_count,
        ranked.latest_report
    FROM ranked
    WHERE ranked.reporter_rank = 1
    ORDER BY ranked.id;
END;
$$;

COMMIT;