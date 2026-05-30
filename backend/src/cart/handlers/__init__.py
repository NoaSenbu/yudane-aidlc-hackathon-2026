"""Cart Intercept Lambda handlers。

- cart_intake.lambda_handler: POST /v1/cart-watch-items（B-04）
- cart_dismiss.dismiss_lambda_handler: DELETE /v1/cart-watch-items/{asin}（B-04）
- cart_list.list_lambda_handler: GET /v1/cart-watch-items / GET /v1/cart-watch-items/{asin}（B-04）
- push_token.register_lambda_handler: POST /v1/push-tokens（B-04）
- notification_dispatcher.lambda_handler: EventBridge Scheduler 起動（B-06）
- cart_attack_scheduler_retry.lambda_handler: rate(15min) リトライバッチ（B-05、NFR Q4=A'）
"""
