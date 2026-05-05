<?php
/**
 * Setup WooCommerce API keys.
 * Run via: wp eval-file /var/www/html/setup-api-keys.php --allow-root
 * 
 * Uses fixed keys that match WOO_KEY/WOO_SECRET in docker-compose.yml
 * consumer_key: char(64) for hash, consumer_secret: char(43) = cs_ + 40 hex
 */

global $wpdb;

// These must match WOO_KEY and WOO_SECRET in docker-compose.yml app service
$consumer_key    = 'ck_0000000000000000000000000000000000000001';
$consumer_secret = 'cs_0000000000000000000000000000000000000001';

$result = $wpdb->insert(
    $wpdb->prefix . 'woocommerce_api_keys',
    array(
        'user_id'         => 1,
        'description'     => 'App',
        'permissions'     => 'read_write',
        'consumer_key'    => wc_api_hash( $consumer_key ),
        'consumer_secret' => $consumer_secret,
        'truncated_key'   => substr( $consumer_key, -7 ),
    ),
    array( '%d', '%s', '%s', '%s', '%s', '%s' )
);

if ( $result ) {
    WP_CLI::success( 'API keys created successfully.' );
} else {
    WP_CLI::error( 'Failed to create API keys: ' . $wpdb->last_error );
}
