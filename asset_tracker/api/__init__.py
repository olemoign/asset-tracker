def includeme(config):
    config.include('asset_tracker.api.assets')
    config.include('asset_tracker.api.datatables')
    config.include('asset_tracker.api.sites')
    config.include('asset_tracker.api.software')
