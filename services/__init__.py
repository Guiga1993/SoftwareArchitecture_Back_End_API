"""Application services and internal integration adapters used by API routes.

Modules in this package translate validated API data into business operations.
``integration_api_client`` owns HTTP transport to the separately deployed
integration service. Address and shipping modules retain backend policy and
adapt stable integration results to the public API contracts.
"""
