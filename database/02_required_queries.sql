
SELECT u.id, u.first_name, u.last_name, u.email, u.phone
FROM users u
WHERE u.role='spectator'
  AND NOT EXISTS (
    SELECT 1 FROM reservations r WHERE r.user_id = u.id
)
ORDER BY u.id;

SELECT DISTINCT u.id, u.first_name, u.last_name, u.email, u.phone
FROM users u
JOIN reservations r ON r.user_id = u.id
JOIN payments p ON p.reservation_id = r.id AND p.status = 'successful'
ORDER BY u.id;

SELECT
    u.id AS user_id,
    u.first_name,
    u.last_name,
    DATE_TRUNC('month', p.paid_at) AS payment_month,
    COUNT(*) AS successful_payment_count,
    SUM(p.amount) AS total_paid_amount
FROM payments p
JOIN reservations r ON r.id = p.reservation_id
JOIN users u ON u.id = r.user_id
WHERE p.status = 'successful'
GROUP BY u.id, u.first_name, u.last_name, DATE_TRUNC('month', p.paid_at)
ORDER BY payment_month DESC, total_paid_amount DESC, user_id;

SELECT
    vpt.user_id,
    vpt.first_name,
    vpt.last_name,
    vpt.venue_city AS city_name,
    COUNT(DISTINCT vpt.reservation_id) AS purchase_count,
    SUM(vpt.quantity) AS ticket_quantity
FROM v_purchased_tickets vpt
GROUP BY vpt.user_id, vpt.first_name, vpt.last_name, vpt.venue_city
HAVING COUNT(DISTINCT vpt.reservation_id) = 1
ORDER BY city_name, last_name, first_name;

SELECT
    vpt.user_id,
    vpt.first_name,
    vpt.last_name,
    vpt.email,
    vpt.phone,
    vpt.payment_id,
    vpt.paid_at,
    vpt.payment_amount,
    vpt.sport_name,
    vpt.home_team,
    vpt.away_team,
    vpt.venue_name,
    vpt.starts_at
FROM v_purchased_tickets vpt
ORDER BY vpt.paid_at DESC, vpt.payment_id DESC
LIMIT 1;

WITH spectator_totals AS (
    SELECT
        u.id,
        u.email,
        u.phone,
        COALESCE(SUM(p.amount) FILTER (WHERE p.status = 'successful'), 0) AS total_paid
    FROM users u
    LEFT JOIN reservations r ON r.user_id = u.id
    LEFT JOIN payments p ON p.reservation_id = r.id
    WHERE u.role = 'spectator' AND u.is_active
    GROUP BY u.id, u.email, u.phone
), totals_with_average AS (
    SELECT *, AVG(total_paid) OVER () AS average_total_paid
    FROM spectator_totals
)
SELECT id AS user_id, email, phone, total_paid, average_total_paid
FROM totals_with_average
WHERE total_paid > average_total_paid
ORDER BY total_paid DESC, user_id;

SELECT
    st.id AS sport_type_id,
    st.name AS sport_name,
    COALESCE(SUM(r.quantity) FILTER (WHERE r.status='paid' AND p.id IS NOT NULL),0) AS sold_ticket_count
FROM sport_types st
LEFT JOIN matches m ON m.sport_type_id=st.id
LEFT JOIN tickets t ON t.match_id=m.id
LEFT JOIN reservations r ON r.ticket_id=t.id
LEFT JOIN payments p ON p.reservation_id=r.id AND p.status='successful'
WHERE st.code IN ('football','volleyball','basketball')
GROUP BY st.id,st.name
ORDER BY sold_ticket_count DESC,sport_name;

SELECT
    u.id AS user_id,
    u.first_name,
    u.last_name,
    SUM(r.quantity) AS tickets_purchased,
    SUM(r.total_amount) AS total_spent
FROM reservations r
JOIN users u ON u.id = r.user_id
JOIN payments p ON p.reservation_id = r.id AND p.status = 'successful'
WHERE p.paid_at >= CURRENT_TIMESTAMP - INTERVAL '7 days'
GROUP BY u.id, u.first_name, u.last_name
ORDER BY tickets_purchased DESC, total_spent DESC, user_id
LIMIT 3;

SELECT
    vpt.venue_city AS city_name,
    SUM(vpt.quantity) AS sold_ticket_count,
    SUM(vpt.total_amount) AS gross_sales
FROM v_purchased_tickets vpt
WHERE vpt.reservation_status = 'paid'
  AND vpt.venue_province = 'تهران'
GROUP BY vpt.venue_city
ORDER BY sold_ticket_count DESC, city_name;

WITH oldest_registered_spectator AS (
    SELECT id
    FROM users
    WHERE role = 'spectator'
    ORDER BY created_at, id
    LIMIT 1
)
SELECT DISTINCT
    vpt.venue_city AS city_name,
    vpt.venue_province AS province_name
FROM v_purchased_tickets vpt
WHERE vpt.user_id = (
    SELECT id
    FROM oldest_registered_spectator
)
ORDER BY province_name, city_name;

SELECT
    u.id,
    u.first_name,
    u.last_name,
    u.email,
    u.phone,
    c.name AS city_name,
    u.is_active,
    u.created_at
FROM users u
LEFT JOIN cities c ON c.id = u.city_id
WHERE u.role = 'support'
ORDER BY u.is_active DESC, u.created_at, u.id;

SELECT
    u.id AS user_id,
    u.first_name,
    u.last_name,
    SUM(r.quantity) AS purchased_ticket_count
FROM users u
JOIN reservations r ON r.user_id = u.id
JOIN payments p ON p.reservation_id = r.id AND p.status = 'successful'
GROUP BY u.id, u.first_name, u.last_name
HAVING SUM(r.quantity) >= 2
ORDER BY purchased_ticket_count DESC, user_id;

SELECT
    u.id AS user_id,
    u.first_name,
    u.last_name,
    SUM(r.quantity) AS football_ticket_count
FROM users u
JOIN reservations r ON r.user_id = u.id
JOIN tickets t ON t.id = r.ticket_id
JOIN matches m ON m.id = t.match_id
JOIN sport_types st ON st.id = m.sport_type_id AND st.code = 'football'
JOIN payments p ON p.reservation_id = r.id AND p.status = 'successful'
GROUP BY u.id, u.first_name, u.last_name
HAVING SUM(r.quantity) BETWEEN 1 AND 2
ORDER BY football_ticket_count DESC, user_id;

SELECT
    u.id AS user_id,
    u.email,
    u.phone
FROM users u
JOIN reservations r ON r.user_id = u.id
JOIN tickets t ON t.id = r.ticket_id
JOIN matches m ON m.id = t.match_id
JOIN sport_types st ON st.id = m.sport_type_id
JOIN payments p ON p.reservation_id = r.id AND p.status = 'successful'
WHERE st.code IN ('football', 'volleyball', 'basketball')
GROUP BY u.id, u.email, u.phone
HAVING COUNT(DISTINCT st.code) = 3
ORDER BY user_id;

SELECT
    vpt.payment_id,
    vpt.paid_at,
    vpt.first_name,
    vpt.last_name,
    vpt.quantity,
    vpt.payment_amount,
    vpt.sport_name,
    vpt.home_team,
    vpt.away_team,
    vpt.venue_name,
    vpt.category_name,
    vpt.section_code,
    vpt.row_code,
    vpt.seat_code
FROM v_purchased_tickets vpt
WHERE vpt.paid_at >= CURRENT_DATE
  AND vpt.paid_at < CURRENT_DATE + INTERVAL '1 day'
ORDER BY vpt.paid_at, vpt.payment_id;

WITH ticket_sales AS (
    SELECT t.id AS ticket_id,
           COALESCE(SUM(r.quantity) FILTER (WHERE p.id IS NOT NULL),0) AS sold_quantity
    FROM tickets t
    LEFT JOIN reservations r ON r.ticket_id=t.id
    LEFT JOIN payments p ON p.reservation_id=r.id AND p.status='successful'
    GROUP BY t.id
), ranked_sales AS (
    SELECT ts.*,DENSE_RANK() OVER(ORDER BY ts.sold_quantity DESC) AS sales_rank
    FROM ticket_sales ts
)
SELECT vc.ticket_id,vc.sport_name,vc.home_team,vc.away_team,vc.venue_name,
       vc.category_name,vc.section_code,rs.sold_quantity
FROM ranked_sales rs JOIN v_ticket_catalog vc ON vc.ticket_id=rs.ticket_id
WHERE rs.sales_rank=2 ORDER BY vc.ticket_id;

WITH support_cancellations AS (
    SELECT r.canceled_by AS support_user_id,COUNT(*) AS canceled_reservation_count,
           SUM(r.quantity) AS canceled_ticket_count
    FROM reservations r JOIN users s ON s.id=r.canceled_by AND s.role='support'
    WHERE r.status IN ('canceled','refunded') GROUP BY r.canceled_by
), all_support_cancellations AS (
    SELECT COUNT(*) AS total_canceled_reservations
    FROM reservations r JOIN users s ON s.id=r.canceled_by AND s.role='support'
    WHERE r.status IN ('canceled','refunded')
), ranked AS (
    SELECT sc.*,ac.total_canceled_reservations,
           ROUND(sc.canceled_reservation_count::NUMERIC/NULLIF(ac.total_canceled_reservations,0)*100,2) AS cancellation_percentage,
           DENSE_RANK() OVER(ORDER BY sc.canceled_reservation_count DESC,sc.canceled_ticket_count DESC) AS cancellation_rank
    FROM support_cancellations sc CROSS JOIN all_support_cancellations ac
)
SELECT u.id AS support_user_id,u.first_name,u.last_name,ranked.canceled_reservation_count,
       ranked.canceled_ticket_count,ranked.total_canceled_reservations,ranked.cancellation_percentage
FROM ranked JOIN users u ON u.id=ranked.support_user_id
WHERE ranked.cancellation_rank=1 ORDER BY support_user_id;

BEGIN;

WITH target_user AS (
    SELECT r.user_id
    FROM reservations r
    WHERE r.status IN ('canceled', 'refunded')
    GROUP BY r.user_id
    ORDER BY SUM(r.quantity) DESC, COUNT(*) DESC, r.user_id
    LIMIT 1
)
UPDATE users u
SET last_name = 'Reddington'
FROM target_user tu
WHERE u.id = tu.user_id
RETURNING u.id, u.first_name, u.last_name;

CREATE TEMP TABLE q19_targets ON COMMIT DROP AS
SELECT r.id,r.ticket_id
FROM reservations r
JOIN users u ON u.id=r.user_id
WHERE u.last_name='Reddington' AND r.status='canceled';

UPDATE reports rp
SET ticket_id=COALESCE(rp.ticket_id,qt.ticket_id),
    reservation_id=NULL,
    payment_id=NULL
FROM q19_targets qt
WHERE rp.reservation_id=qt.id
   OR rp.payment_id IN (SELECT p.id FROM payments p WHERE p.reservation_id=qt.id);

DELETE FROM seat_change_requests scr
USING q19_targets qt
WHERE scr.reservation_id=qt.id;

DELETE FROM cancellation_requests cr
USING q19_targets qt
WHERE cr.reservation_id=qt.id
  AND NOT EXISTS (SELECT 1 FROM refunds rf WHERE rf.cancellation_request_id=cr.id);

DELETE FROM payments p
USING q19_targets qt
WHERE p.reservation_id=qt.id
  AND p.status<>'successful';

DELETE FROM reservations r
USING q19_targets qt
WHERE r.id=qt.id
RETURNING r.id,r.user_id,r.ticket_id,r.quantity;

CREATE TEMP TABLE q20_targets ON COMMIT DROP AS
SELECT id,ticket_id FROM reservations WHERE status='canceled';

UPDATE reports rp
SET ticket_id=COALESCE(rp.ticket_id,qt.ticket_id),
    reservation_id=NULL,
    payment_id=NULL
FROM q20_targets qt
WHERE rp.reservation_id=qt.id
   OR rp.payment_id IN (SELECT p.id FROM payments p WHERE p.reservation_id=qt.id);

DELETE FROM seat_change_requests scr
USING q20_targets qt
WHERE scr.reservation_id=qt.id;

DELETE FROM cancellation_requests cr
USING q20_targets qt
WHERE cr.reservation_id=qt.id
  AND NOT EXISTS (SELECT 1 FROM refunds rf WHERE rf.cancellation_request_id=cr.id);

DELETE FROM payments p
USING q20_targets qt
WHERE p.reservation_id=qt.id
  AND p.status<>'successful';

DELETE FROM reservations r
USING q20_targets qt
WHERE r.id=qt.id
RETURNING r.id,r.user_id,r.ticket_id,r.quantity;

ROLLBACK;

BEGIN;

WITH sold_yesterday_at_azadi AS (
    SELECT DISTINCT r.ticket_id
    FROM payments p
    JOIN reservations r ON r.id = p.reservation_id
    JOIN tickets t ON t.id = r.ticket_id
    JOIN matches m ON m.id = t.match_id
    JOIN venues v ON v.id = m.venue_id
    WHERE p.status = 'successful'
      AND p.paid_at >= CURRENT_DATE - INTERVAL '1 day'
      AND p.paid_at < CURRENT_DATE
      AND v.name = 'Azadi Stadium'
)
UPDATE tickets t
SET price = ROUND(t.price * 0.90, 2)
FROM sold_yesterday_at_azadi s
WHERE t.id = s.ticket_id
RETURNING t.id, t.match_id, t.price AS reduced_price;

ROLLBACK;

WITH per_ticket AS (
    SELECT ticket_id,COUNT(*) AS total_reports,
           DENSE_RANK() OVER(ORDER BY COUNT(*) DESC) AS report_rank
    FROM reports WHERE ticket_id IS NOT NULL GROUP BY ticket_id
), most_reported AS (
    SELECT ticket_id,total_reports FROM per_ticket WHERE report_rank=1
)
SELECT r.ticket_id,vc.sport_name,vc.home_team,vc.away_team,
       rc.code AS report_category_code,rc.name AS report_category,r.subject,
       COUNT(*) AS report_count_for_subject,mr.total_reports AS total_reports_for_ticket
FROM reports r
JOIN most_reported mr ON mr.ticket_id=r.ticket_id
JOIN report_categories rc ON rc.id=r.category_id
JOIN v_ticket_catalog vc ON vc.ticket_id=r.ticket_id
GROUP BY r.ticket_id,vc.sport_name,vc.home_team,vc.away_team,rc.code,rc.name,r.subject,mr.total_reports
ORDER BY r.ticket_id,report_count_for_subject DESC,report_category,subject;

