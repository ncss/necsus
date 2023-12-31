import starlette.config

# Make all tests run using an in-memory database.
starlette.config.environ['NECSUS_DB'] = ':memory:'
