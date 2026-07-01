app_name = "reformiqo_pe"
app_title = "Reformiqo PE"
app_publisher = "Reformiqo Team"
app_description = "Generic / Direct GL Payment Entry customization for standard ERPNext Payment Entry (FRD v2.0)"
app_email = "noreply@reformiqo.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "reformiqo_pe",
# 		"logo": "/assets/reformiqo_pe/logo.png",
# 		"title": "Reformiqo PE",
# 		"route": "/reformiqo_pe",
# 		"has_permission": "reformiqo_pe.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/reformiqo_pe/css/reformiqo_pe.css"
# app_include_js = "/assets/reformiqo_pe/js/reformiqo_pe.js"

# include js, css files in header of web template
# web_include_css = "/assets/reformiqo_pe/css/reformiqo_pe.css"
# web_include_js = "/assets/reformiqo_pe/js/reformiqo_pe.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "reformiqo_pe/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "reformiqo_pe/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "reformiqo_pe.utils.jinja_methods",
# 	"filters": "reformiqo_pe.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "reformiqo_pe.install.before_install"
# after_install = "reformiqo_pe.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "reformiqo_pe.uninstall.before_uninstall"
# after_uninstall = "reformiqo_pe.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "reformiqo_pe.utils.before_app_install"
# after_app_install = "reformiqo_pe.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "reformiqo_pe.utils.before_app_uninstall"
# after_app_uninstall = "reformiqo_pe.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "reformiqo_pe.build.after_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "reformiqo_pe.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"reformiqo_pe.tasks.all"
# 	],
# 	"daily": [
# 		"reformiqo_pe.tasks.daily"
# 	],
# 	"hourly": [
# 		"reformiqo_pe.tasks.hourly"
# 	],
# 	"weekly": [
# 		"reformiqo_pe.tasks.weekly"
# 	],
# 	"monthly": [
# 		"reformiqo_pe.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "reformiqo_pe.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "reformiqo_pe.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "reformiqo_pe.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "reformiqo_pe.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["reformiqo_pe.utils.before_request"]
# after_request = ["reformiqo_pe.utils.after_request"]

# Job Events
# ----------
# before_job = ["reformiqo_pe.utils.before_job"]
# after_job = ["reformiqo_pe.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"reformiqo_pe.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []



# ────────────────────────────────────────────────────────────────────── #
# ABP2-I481 — Generic / Direct GL Payment Entry (FRD v2.0)
# ────────────────────────────────────────────────────────────────────── #

# Idempotent CF upsert every migrate. Property Setters belong in code —
# [[feedback-property-setters-in-code]].
after_install = "reformiqo_pe.setup.after_install"
after_migrate = "reformiqo_pe.setup.after_migrate"
before_uninstall = "reformiqo_pe.setup.before_uninstall"

# Server hooks (Phase 4). Wired here so the module gets imported on
# every request; the actual functions live in overrides/.
doc_events = {
	"Payment Entry": {
		# CRITICAL — autowire runs on before_validate so paid_amount /
		# paid_from / paid_to are populated BEFORE ERPNext's own
		# validate throws "Paid Amount is mandatory". Our validate
		# then runs and enforces the accounting-integrity checks.
		"before_validate": [
			"reformiqo_pe.overrides.payment_entry_direct_gl.autowire_native_fields_before_submit",
		],
		"validate": [
			"reformiqo_pe.overrides.payment_entry_direct_gl.validate_direct_gl_mode",
		],
	},
}

# Client Script bundle (Phase 3). Shipped as an included JS asset so
# every Payment Entry form loads the mode-toggle wiring on refresh.
doctype_js = {
	"Payment Entry": "public/js/payment_entry_direct_gl.js",
}

# Fixtures — the 2 child DocTypes ship as code (module.txt / doctype
# folder), but the Custom Fields themselves are managed by setup.py so
# they never drift on cloud.
fixtures = []
