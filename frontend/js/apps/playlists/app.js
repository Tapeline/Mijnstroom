define(function (require) {
	var PlaylistsCollection = require('./collections/PlaylistsCollection');
	var MainView = require('./views/MainView');

	return {
		run: function(viewManager) {
			var playlistsCollection = new PlaylistsCollection();
			playlistsCollection.fetch({
				success: function (playlists) {
					var view = new MainView({collection: playlists});
					viewManager.show(view);
				}
			});
		}
	};
});