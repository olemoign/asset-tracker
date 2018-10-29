def includeme(config):
    config.include('asset_tracker.views.assets')
    config.include('asset_tracker.views.sites')
    config.include('asset_tracker.views.utilities')
