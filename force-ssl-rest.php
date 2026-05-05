<?php
/**
 * Plugin Name: Force SSL for WooCommerce REST API
 * Description: Tells WordPress that requests are over SSL, enabling WooCommerce basic auth over HTTP (Docker dev)
 */

// Only fake SSL for REST API requests to avoid redirect loops
if ( isset( $_SERVER['REQUEST_URI'] ) && strpos( $_SERVER['REQUEST_URI'], '/wp-json/' ) !== false ) {
    $_SERVER['HTTPS'] = 'on';
}
if ( isset( $_GET['rest_route'] ) ) {
    $_SERVER['HTTPS'] = 'on';
}
