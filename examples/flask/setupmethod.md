# ⚡ Blast radius: `src.flask.sansio.scaffold.setupmethod`

**114** definitions across **10** files depend on this change.
 🔥 **7** high-impact **untested** hotspot(s) need review.

## 🔥 Untested hotspots (review first)

| Definition | File | Depth | Fan-in | Risk |
| --- | --- | --: | --: | --: |
| `src.flask.sansio.blueprints.Blueprint.record_once` | `src/flask/sansio/blueprints.py` | 1 | 10 | 20.0 |
| `src.flask.sansio.scaffold.Scaffold._method_route` | `src/flask/sansio/scaffold.py` | 2 | 5 | 5.0 |
| `src.flask.sansio.app.App.add_template_filter` | `src/flask/sansio/app.py` | 1 | 2 | 4.0 |
| `src.flask.sansio.app.App.add_template_global` | `src/flask/sansio/app.py` | 1 | 2 | 4.0 |
| `src.flask.sansio.app.App.add_template_test` | `src/flask/sansio/app.py` | 1 | 2 | 4.0 |
| `src.flask.sansio.blueprints.Blueprint.add_app_template_global` | `src/flask/sansio/blueprints.py` | 1 | 2 | 4.0 |
| `src.flask.sansio.blueprints.Blueprint.record` | `src/flask/sansio/blueprints.py` | 1 | 2 | 4.0 |

## Affected definitions by file

### `src/flask/app.py`

| Definition | Type | Depth | Fan-in | Tested |
| --- | --- | --: | --: | :-: |
| `__init__` | Method | 2 | 0 | — |

### `src/flask/sansio/app.py`

| Definition | Type | Depth | Fan-in | Tested |
| --- | --- | --: | --: | :-: |
| `add_template_filter` | DecoratedMethod | 1 | 2 | — |
| `add_template_global` | DecoratedMethod | 1 | 2 | — |
| `add_template_test` | DecoratedMethod | 1 | 2 | — |
| `add_url_rule` | DecoratedMethod | 1 | 1 | — |
| `register_blueprint` | DecoratedMethod | 1 | 2 | ✅ |
| `shell_context_processor` | DecoratedMethod | 1 | 0 | — |
| `teardown_appcontext` | DecoratedMethod | 1 | 0 | — |
| `template_filter` | DecoratedMethod | 1 | 0 | — |
| `template_global` | DecoratedMethod | 1 | 0 | — |
| `template_test` | DecoratedMethod | 1 | 0 | — |
| `decorator` | Function | 2 | 0 | — |
| `decorator` | Function | 2 | 0 | — |
| `decorator` | Function | 2 | 0 | — |

### `src/flask/sansio/blueprints.py`

| Definition | Type | Depth | Fan-in | Tested |
| --- | --- | --: | --: | :-: |
| `add_app_template_filter` | DecoratedMethod | 1 | 6 | ✅ |
| `add_app_template_global` | DecoratedMethod | 1 | 2 | — |
| `add_app_template_test` | DecoratedMethod | 1 | 6 | ✅ |
| `add_url_rule` | DecoratedMethod | 1 | 2 | ✅ |
| `after_app_request` | DecoratedMethod | 1 | 1 | ✅ |
| `app_context_processor` | DecoratedMethod | 1 | 1 | ✅ |
| `app_errorhandler` | DecoratedMethod | 1 | 1 | ✅ |
| `app_template_filter` | DecoratedMethod | 1 | 5 | ✅ |
| `app_template_global` | DecoratedMethod | 1 | 1 | ✅ |
| `app_template_test` | DecoratedMethod | 1 | 5 | ✅ |
| `app_url_defaults` | DecoratedMethod | 1 | 1 | ✅ |
| `app_url_value_preprocessor` | DecoratedMethod | 1 | 1 | ✅ |
| `before_app_request` | DecoratedMethod | 1 | 1 | ✅ |
| `record` | DecoratedMethod | 1 | 2 | — |
| `record_once` | DecoratedMethod | 1 | 10 | — |
| `register_blueprint` | DecoratedMethod | 1 | 7 | ✅ |
| `teardown_app_request` | DecoratedMethod | 1 | 1 | ✅ |
| `decorator` | Function | 2 | 0 | — |
| `decorator` | Function | 2 | 0 | — |
| `decorator` | Function | 2 | 0 | — |
| `decorator` | Function | 2 | 0 | — |
| `add_url_rule` | Method | 2 | 1 | — |
| `register` | Method | 3 | 1 | — |

### `src/flask/sansio/scaffold.py`

| Definition | Type | Depth | Fan-in | Tested |
| --- | --- | --: | --: | :-: |
| `add_url_rule` | DecoratedMethod | 1 | 1 | — |
| `after_request` | DecoratedMethod | 1 | 2 | ✅ |
| `before_request` | DecoratedMethod | 1 | 3 | ✅ |
| `context_processor` | DecoratedMethod | 1 | 2 | ✅ |
| `delete` | DecoratedMethod | 1 | 0 | — |
| `endpoint` | DecoratedMethod | 1 | 1 | ✅ |
| `errorhandler` | DecoratedMethod | 1 | 6 | ✅ |
| `get` | DecoratedMethod | 1 | 2 | ✅ |
| `patch` | DecoratedMethod | 1 | 0 | — |
| `post` | DecoratedMethod | 1 | 0 | — |
| `put` | DecoratedMethod | 1 | 0 | — |
| `register_error_handler` | DecoratedMethod | 1 | 2 | ✅ |
| `route` | DecoratedMethod | 1 | 34 | ✅ |
| `teardown_request` | DecoratedMethod | 1 | 2 | ✅ |
| `url_defaults` | DecoratedMethod | 1 | 2 | ✅ |
| `url_value_preprocessor` | DecoratedMethod | 1 | 1 | ✅ |
| `_method_route` | Method | 2 | 5 | — |
| `decorator` | Function | 2 | 0 | — |
| `decorator` | Function | 2 | 0 | — |

### `tests/test_basic.py` *(tests)*

| Definition | Type | Depth | Fan-in | Tested |
| --- | --- | --: | --: | :-: |
| `test_inject_blueprint_url_defaults` | Function | 2 | 0 | ✅ |
| `test_response_type_errors` | Function | 2 | 0 | ✅ |
| `test_server_name_matching` | DecoratedFunction | 2 | 0 | ✅ |
| `test_server_name_subdomain` | Function | 2 | 0 | ✅ |
| `test_static_folder_with_ending_slash` | Function | 2 | 0 | ✅ |
| `test_subdomain_basic_support` | Function | 2 | 0 | ✅ |
| `test_subdomain_matching` | Function | 2 | 0 | ✅ |
| `test_subdomain_matching_other_name` | DecoratedFunction | 2 | 0 | ✅ |
| `test_subdomain_matching_with_ports` | Function | 2 | 0 | ✅ |

### `tests/test_blueprints.py` *(tests)*

| Definition | Type | Depth | Fan-in | Tested |
| --- | --- | --: | --: | :-: |
| `test_add_template_filter` | Function | 2 | 0 | ✅ |
| `test_add_template_filter_with_name` | Function | 2 | 0 | ✅ |
| `test_add_template_filter_with_name_and_template` | Function | 2 | 0 | ✅ |
| `test_add_template_filter_with_template` | Function | 2 | 0 | ✅ |
| `test_add_template_test` | Function | 2 | 0 | ✅ |
| `test_add_template_test_with_name` | Function | 2 | 0 | ✅ |
| `test_add_template_test_with_name_and_template` | Function | 2 | 0 | ✅ |
| `test_add_template_test_with_template` | Function | 2 | 0 | ✅ |
| `test_app_request_processing` | Function | 2 | 0 | ✅ |
| `test_app_url_processors` | Function | 2 | 0 | ✅ |
| `test_blueprint_app_error_handling` | Function | 2 | 0 | ✅ |
| `test_blueprint_prefix_slash` | DecoratedFunction | 2 | 0 | ✅ |
| `test_blueprint_renaming` | Function | 2 | 0 | ✅ |
| `test_blueprint_specific_error_handling` | Function | 2 | 0 | ✅ |
| `test_blueprint_specific_user_error_handling` | Function | 2 | 0 | ✅ |
| `test_blueprint_url_defaults` | Function | 2 | 0 | ✅ |
| `test_blueprint_url_processors` | Function | 2 | 0 | ✅ |
| `test_child_and_parent_subdomain` | Function | 2 | 0 | ✅ |
| `test_context_processing` | Function | 2 | 0 | ✅ |
| `test_dotted_names_from_app` | Function | 2 | 0 | ✅ |
| `test_empty_url_defaults` | Function | 2 | 0 | ✅ |
| `test_endpoint_decorator` | Function | 2 | 0 | ✅ |
| `test_nested_blueprint` | Function | 2 | 0 | ✅ |
| `test_nested_callback_order` | Function | 2 | 0 | ✅ |
| `test_nesting_subdomains` | Function | 2 | 0 | ✅ |
| `test_nesting_url_prefixes` | DecoratedFunction | 2 | 0 | ✅ |
| `test_request_processing` | Function | 2 | 0 | ✅ |
| `test_route_decorator_custom_endpoint` | Function | 2 | 0 | ✅ |
| `test_route_decorator_custom_endpoint_with_dots` | Function | 2 | 0 | ✅ |
| `test_self_registration` | Function | 2 | 0 | ✅ |
| `test_template_filter` | Function | 2 | 0 | ✅ |
| `test_template_filter_after_route_with_template` | Function | 2 | 0 | ✅ |
| `test_template_filter_with_name` | Function | 2 | 0 | ✅ |
| `test_template_filter_with_name_and_template` | Function | 2 | 0 | ✅ |
| `test_template_filter_with_template` | Function | 2 | 0 | ✅ |
| `test_template_global` | Function | 2 | 0 | ✅ |
| `test_template_test` | Function | 2 | 0 | ✅ |
| `test_template_test_after_route_with_template` | Function | 2 | 0 | ✅ |
| `test_template_test_with_name` | Function | 2 | 0 | ✅ |
| `test_template_test_with_name_and_template` | Function | 2 | 0 | ✅ |
| `test_template_test_with_template` | Function | 2 | 0 | ✅ |

### `tests/test_session_interface.py` *(tests)*

| Definition | Type | Depth | Fan-in | Tested |
| --- | --- | --: | --: | :-: |
| `test_open_session_with_endpoint` | Function | 2 | 0 | ✅ |

### `tests/test_signals.py` *(tests)*

| Definition | Type | Depth | Fan-in | Tested |
| --- | --- | --: | --: | :-: |
| `test_before_render_template` | Function | 2 | 0 | ✅ |
| `test_request_exception_signal` | Function | 2 | 0 | ✅ |
| `test_request_signals` | Function | 2 | 0 | ✅ |

### `tests/test_testing.py` *(tests)*

| Definition | Type | Depth | Fan-in | Tested |
| --- | --- | --: | --: | :-: |
| `test_blueprint_with_subdomain` | Function | 2 | 0 | ✅ |
| `test_subdomain` | Function | 2 | 0 | ✅ |

### `tests/test_user_error_handler.py` *(tests)*

| Definition | Type | Depth | Fan-in | Tested |
| --- | --- | --: | --: | :-: |
| `test_default_error_handler` | Function | 2 | 0 | ✅ |
| `test_error_handler_blueprint` | Function | 2 | 0 | ✅ |
