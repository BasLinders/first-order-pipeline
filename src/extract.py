from google.cloud import bigquery
import logging

logger = logging.getLogger(__name__)

def fetch_bigquery_data() -> list[dict]:
    logger.info("Initializing BigQuery client...")
    client = bigquery.Client()
    
    # Different queries:
    agg_query = """
        DECLARE start_date STRING DEFAULT 'yyyy-mm-dd';
        DECLARE end_date STRING DEFAULT 'yyyy-mm-dd';
        DECLARE variant_a STRING DEFAULT '';
        DECLARE variant_b STRING DEFAULT '';
        DECLARE variant_c STRING DEFAULT '';
        
        WITH user_initial_exposure AS (
          SELECT
            user_pseudo_id,
            (SELECT value.string_value FROM UNNEST(event_params) 
             WHERE key = 'exp_variant_string' 
               AND value.string_value IS NOT NULL
               AND value.string_value LIKE 'EXPERIMENT-ID%') AS exp_variant_string,
            ROW_NUMBER() OVER (PARTITION BY user_pseudo_id ORDER BY event_timestamp ASC) AS rn
          FROM
            `environment.dataset.events_*`
          WHERE
            _TABLE_SUFFIX BETWEEN FORMAT_DATE('%Y%m%d', PARSE_DATE('%Y-%m-%d', start_date))
                            AND FORMAT_DATE('%Y%m%d', PARSE_DATE('%Y-%m-%d', end_date))
          AND user_pseudo_id IS NOT NULL
          AND EXISTS (
            SELECT 1 FROM UNNEST(event_params)
            WHERE key = 'exp_variant_string'
              AND value.string_value IS NOT NULL
              AND value.string_value LIKE 'EXPERIMENT-ID%'
          )
        ),
        
        variant_data AS (
         SELECT
          user_pseudo_id AS variant_user_pseudo_id,
          CASE
           WHEN exp_variant_string = variant_a THEN 'A'
           WHEN exp_variant_string = variant_b THEN 'B'
           --WHEN exp_variant_string = variant_c THEN 'C'
           ELSE 'Other'
          END AS experience_variant_label
         FROM
          user_initial_exposure
         WHERE rn = 1
        ),
        
        ecommerce_data AS ( -- Deze fixen vanwege 'fan out effect'
         SELECT
          user_pseudo_id AS ecommerce_user_pseudo_id,
          SUM(ecommerce.purchase_revenue) AS purchase_revenue,
          SUM(ecommerce.total_item_quantity) AS total_item_quantity,
          COUNT(DISTINCT ecommerce.transaction_id) AS transaction_id
         FROM
          `environment.dataset.events_*`
         WHERE
          _TABLE_SUFFIX BETWEEN FORMAT_DATE('%Y%m%d', PARSE_DATE('%Y-%m-%d', start_date)) AND FORMAT_DATE('%Y%m%d', PARSE_DATE('%Y-%m-%d', end_date))
          AND event_name = 'purchase'
          AND user_pseudo_id IS NOT NULL
         GROUP BY
          user_pseudo_id
        ),
        
        add_to_cart_data AS (
          SELECT
            user_pseudo_id AS atc_user_pseudo_id
          FROM
            `environment.dataset.events_*`
          WHERE
            _TABLE_SUFFIX BETWEEN FORMAT_DATE('%Y%m%d', PARSE_DATE('%Y-%m-%d', start_date)) AND FORMAT_DATE('%Y%m%d', PARSE_DATE('%Y-%m-%d', end_date))
            AND event_name = 'add_to_cart'
            AND user_pseudo_id IS NOT NULL
          GROUP BY
            user_pseudo_id -- DISTINCT user_pseudo_id who added to cart
        ),
        
        device_data AS (
         SELECT
          user_pseudo_id AS device_user_pseudo_id,
          MAX(CASE WHEN device.category = 'mobile' THEN 1 ELSE 0 END) AS is_mobile_user,
          MAX(CASE WHEN device.category = 'desktop' THEN 1 ELSE 0 END) AS is_desktop_user
         FROM
          `environment.dataset.events_*`
         WHERE
          _TABLE_SUFFIX BETWEEN FORMAT_DATE('%Y%m%d', PARSE_DATE('%Y-%m-%d', start_date)) AND FORMAT_DATE('%Y%m%d', PARSE_DATE('%Y-%m-%d', end_date))
          AND user_pseudo_id IS NOT NULL
         GROUP BY
          user_pseudo_id
        ),
        
        ideal_users AS (
          SELECT DISTINCT
          user_pseudo_id
         FROM
          `environment.dataset.events_*`,
          UNNEST(event_params) AS params
         WHERE
          _TABLE_SUFFIX BETWEEN FORMAT_DATE('%Y%m%d', PARSE_DATE('%Y-%m-%d', start_date)) AND FORMAT_DATE('%Y%m%d', PARSE_DATE('%Y-%m-%d', end_date))
          AND event_name = 'add_payment_info'
          AND params.key = 'payment_type'
          AND params.value.string_value LIKE '%iDEAL%'
          AND user_pseudo_id IS NOT NULL
        ),
        
        combined_data AS (
         SELECT
          vd.variant_user_pseudo_id,
          vd.experience_variant_label,
          COALESCE(ed.purchase_revenue, 0) AS purchase_revenue,
          COALESCE(ed.total_item_quantity, 0) AS total_item_quantity,
          ed.transaction_id,
          COALESCE(dd.is_mobile_user, 0) AS is_mobile_user,
          COALESCE(dd.is_desktop_user, 0) AS is_desktop_user,
          atc.atc_user_pseudo_id AS added_to_cart,
          CASE WHEN iu.user_pseudo_id IS NOT NULL THEN 1 ELSE 0 END AS paid_with_ideal
         FROM
          variant_data vd
         LEFT JOIN
          ecommerce_data ed
         ON
          vd.variant_user_pseudo_id = ed.ecommerce_user_pseudo_id
         LEFT JOIN
          device_data dd
         ON
          vd.variant_user_pseudo_id = dd.device_user_pseudo_id
         LEFT JOIN
          add_to_cart_data atc
         ON 
          vd.variant_user_pseudo_id = atc.atc_user_pseudo_id
        ),
        
        aggregated_data AS (
         SELECT
          experience_variant_label,
          COUNT(DISTINCT CASE WHEN transaction_id IS NOT NULL THEN variant_user_pseudo_id ELSE NULL END) AS with_transaction,
          SUM(CASE WHEN transaction_id IS NOT NULL THEN transaction_id ELSE 0 END) AS total_transactions,
          --COUNT(DISTINCT CASE WHEN transaction_id IS NULL THEN variant_user_pseudo_id ELSE NULL END) AS without_transaction,
          COUNT(DISTINCT CASE WHEN experience_variant_label = 'A' THEN variant_user_pseudo_id ELSE NULL END) AS visitors_a,
          COUNT(DISTINCT CASE WHEN experience_variant_label = 'B' THEN variant_user_pseudo_id ELSE NULL END) AS visitors_b,
          --COUNT(DISTINCT CASE WHEN experience_variant_label = 'C' THEN variant_user_pseudo_id ELSE NULL END) AS visitors_c,
          COUNT(DISTINCT CASE WHEN experience_variant_label IS NOT NULL AND is_mobile_user = 1 THEN variant_user_pseudo_id ELSE NULL END) AS mobile_user_count,
          COUNT(DISTINCT CASE WHEN transaction_id IS NOT NULL AND experience_variant_label IS NOT NULL AND is_mobile_user = 1 THEN variant_user_pseudo_id ELSE NULL END) AS mobile_buyers,
          COUNT(DISTINCT CASE WHEN experience_variant_label IS NOT NULL AND is_desktop_user = 1 THEN variant_user_pseudo_id ELSE NULL END) AS desktop_user_count,
          COUNT(DISTINCT CASE WHEN transaction_id IS NOT NULL AND experience_variant_label IS NOT NULL AND is_desktop_user = 1 THEN variant_user_pseudo_id ELSE NULL END) AS desktop_buyers,
          CASE WHEN experience_variant_label = 'A' THEN ROUND(SUM(purchase_revenue) / NULLIF(COUNT(CASE WHEN transaction_id IS NOT NULL THEN transaction_id END), 0),2) ELSE NULL END AS average_order_value_a,
          CASE WHEN experience_variant_label = 'B' THEN ROUND(SUM(purchase_revenue) / NULLIF(COUNT(CASE WHEN transaction_id IS NOT NULL THEN transaction_id END), 0),2) ELSE NULL END AS average_order_value_b,
          --CASE WHEN experience_variant_label = 'C' THEN ROUND(SUM(purchase_revenue) / NULLIF(COUNT(CASE WHEN transaction_id IS NOT NULL THEN transaction_id END), 0),2) ELSE NULL END AS average_order_value_c
          COUNT(DISTINCT CASE WHEN experience_variant_label = 'A' THEN added_to_cart ELSE NULL END) AS added_to_cart_a,
          COUNT(DISTINCT CASE WHEN experience_variant_label = 'B' THEN added_to_cart ELSE NULL END) AS added_to_cart_b,
         FROM
          combined_data
         GROUP BY
          experience_variant_label
         ORDER BY
          experience_variant_label
        )
        
        SELECT * FROM aggregated_data;
    """

    cont_query = """
        DECLARE start_date STRING DEFAULT 'YYYY-MM-DD';
        DECLARE end_date STRING DEFAULT 'YYYY-MM-DD';
        DECLARE variant_a STRING DEFAULT '';
        DECLARE variant_b STRING DEFAULT '';
        DECLARE device_filter STRING DEFAULT 'all'; # Options: 'all', 'desktop', 'mobile'
        
        WITH single_scan AS (
          SELECT
            user_pseudo_id,
            event_name,
            event_timestamp,
            ecommerce,
            (SELECT p.value.string_value
             FROM UNNEST(event_params) AS p
             WHERE p.key = 'exp_variant_string'
             LIMIT 1) AS exp_variant_string
          FROM
            `environment.dataset.table`
          WHERE
            _TABLE_SUFFIX BETWEEN FORMAT_DATE('%Y%m%d', PARSE_DATE('%Y-%m-%d', start_date))
            AND FORMAT_DATE('%Y%m%d', PARSE_DATE('%Y-%m-%d', end_date))
            AND (
              event_name = 'purchase'
              OR EXISTS (
                SELECT 1 FROM UNNEST(event_params) AS p
                WHERE p.key = 'exp_variant_string'
              )
            )
            AND user_pseudo_id IS NOT NULL
        ),
        
        user_initial_exposure AS (
          SELECT
            user_pseudo_id,
            exp_variant_string,
            ROW_NUMBER() OVER (
              PARTITION BY user_pseudo_id
              ORDER BY event_timestamp ASC
            ) AS rn
          FROM single_scan
          WHERE
            exp_variant_string IS NOT NULL
            AND exp_variant_string LIKE 'EXP-ID-%'
        ),
        
        variant_data AS (
          SELECT
            user_pseudo_id,
            CASE
              WHEN exp_variant_string = variant_a THEN 'A'
              WHEN exp_variant_string = variant_b THEN 'B'
              ELSE 'Other'
            END AS experience_variant_label
          FROM user_initial_exposure
          WHERE rn = 1
        ),
        
        device_data AS (
          SELECT
            user_pseudo_id AS device_user_pseudo_id,
            CASE
              WHEN COUNTIF(device.category = 'desktop') >= COUNTIF(device.category = 'mobile')
                THEN 'desktop'
              ELSE 'mobile'
            END AS primary_device
          FROM
            `environment.dataset.table`
          WHERE
            _TABLE_SUFFIX BETWEEN FORMAT_DATE('%Y%m%d', PARSE_DATE('%Y-%m-%d', start_date))
            AND FORMAT_DATE('%Y%m%d', PARSE_DATE('%Y-%m-%d', end_date))
            AND user_pseudo_id IS NOT NULL
            AND device.category IN ('desktop', 'mobile')
          GROUP BY
            user_pseudo_id
        ),
        
        ecommerce_data AS (
          SELECT
            user_pseudo_id,
            ecommerce.transaction_id AS transaction_id,
            SUM(ecommerce.purchase_revenue) AS purchase_revenue,
            SUM(ecommerce.total_item_quantity) AS total_item_quantity
          FROM single_scan
          WHERE
            event_name = 'purchase'
            AND ecommerce.purchase_revenue IS NOT NULL
            AND ecommerce.purchase_revenue <> 0.0
          GROUP BY
            user_pseudo_id, transaction_id
        )
        
        SELECT
          vd.user_pseudo_id AS variant_user_pseudo_id,
          vd.experience_variant_label,
          ed.purchase_revenue,
          ed.total_item_quantity,
          ed.transaction_id
        FROM
          variant_data vd
          INNER JOIN ecommerce_data ed ON vd.user_pseudo_id = ed.user_pseudo_id
          INNER JOIN device_data    dd ON vd.user_pseudo_id = dd.device_user_pseudo_id
        WHERE
          device_filter = 'all'
          OR dd.primary_device = device_filter
        ORDER BY
          ed.purchase_revenue DESC;
    """
    
    try:
        query_job = client.query() # write logic flow to select the right query for the right engine (agg_query, cont_query)
        results = query_job.result()
        
        # Convert BigQuery RowIterator to a list of standard Python dictionaries
        rows = [dict(row) for row in results]
        logger.info(f"Successfully extracted {len(rows)} experiments.")
        return rows
    except Exception as e:
        logger.error(f"Failed to fetch data from BigQuery: {e}")
        raise
