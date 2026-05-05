<?php
/**
 * Plugin Name: Force REST API Basic Auth
 * Description: Allow WooCommerce REST API basic auth over HTTP (for development/Docker)
 */

add_filter('woocommerce_rest_is_ssl', '__return_true');
