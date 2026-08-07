define(function (require) {
	var PlaylistsCollection = require('./collections/PlaylistsCollection');
	var Playlist = require('./models/Playlist');
	var MainView = require('./views/MainView');
	var DetailView = require('./views/DetailView');
	var CreateView = require('./views/CreateView');

	function buildQuery(filters) {
		var query = {};
		if (filters) {
			['title', 'artist', 'album'].forEach(function (k) {
				if (filters[k]) { query[k] = filters[k]; }
			});
			if (filters.include_unset) { query.include_unset = 'true'; }
		}
		return query;
	}

	var api = {
		run: function (viewManager, filters) {
			var playlists = new PlaylistsCollection();
			playlists.fetch({
				data: buildQuery(filters),
				success: function () {
					viewManager.show(new MainView({
						collection: playlists,
						filters: filters || {},
						onFilter: function (newFilters) {
							api.run(viewManager, newFilters);
						}
					}));
				},
				error: function () {
					viewManager.show(new MainView({
						collection: new PlaylistsCollection(),
						filters: filters || {},
						error: 'Failed to load playlists'
					}));
				}
			});
		},

		detail: function (viewManager, uid) {
			var playlist = new Playlist({ uid: uid });
			playlist.fetch({
				success: function () {
					viewManager.show(new DetailView({ model: playlist }));
				},
				error: function () {
					viewManager.show(new DetailView({
						model: new Playlist({ uid: uid }),
						error: 'Failed to load playlist'
					}));
				}
			});
		},

		create: function (viewManager) {
			viewManager.show(new CreateView({ model: new Playlist() }));
		}
	};

	return api;
});
