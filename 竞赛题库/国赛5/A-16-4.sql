CREATE PROCEDURE sp_FireAlert(IN zone_id INT, IN smoke_level DECIMAL(5,2), IN temp DECIMAL(5,2))
BEGIN
    INSERT INTO fire_alerts(zone_id, smoke_level, temperature, alert_time)
    VALUES(zone_id, smoke_level, temp, NOW());
    IF smoke_level > 80 OR temp > 60 THEN
        UPDATE fire_zones SET status='danger' WHERE id=zone_id;
    END IF;
END;