define(function (require) {
	var TracksCollection = require('./collections/TracksCollection');
	var Track = require('./models/Track');
	var MainView = require('./views/MainView');
	var DetailView = require('./views/DetailView');

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
			var tracksCollection = new TracksCollection();
			tracksCollection.fetch({
				data: buildQuery(filters),
				success: function (tracks) {
					var view = new MainView({
						collection: tracks,
						filters: filters || {},
						onFilter: function (newFilters) {
							api.run(viewManager, newFilters);
						}
					});
					viewManager.show(view);
				},
				error: function () {
					viewManager.show(new MainView({
						collection: new TracksCollection(),
						filters: filters || {},
						error: 'Failed to load tracks'
					}));
				}
			});
		},

		detail: function (viewManager, uid) {
			var track = new Track({ uid: uid });
			track.fetch({
				success: function () {
          Backbone.ajax({
            url: '/api/tracks/' + uid + "/formats",
            type: 'GET',
            success: function(data) {
              track.set('formats', data);
              console.log(track)
					    viewManager.show(new DetailView({ model: track }));
            }
          });
				},
				error: function () {
					viewManager.show(new DetailView({
						model: new Track({ uid: uid }),
						error: 'Failed to load track'
					}));
				}
			});
		}
	};

	return api;
});
