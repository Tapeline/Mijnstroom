define(function (require) {
	var Backbone = require('Backbone');
	var ChoiceView = require('./views/ChoiceView');
	var PrepareView = require('./views/PrepareView');
	var ImportView = require('./views/ImportView');
	var PreparePlaylistView = require('./views/PreparePlaylistView');
	var ImportPlaylistView = require('./views/ImportPlaylistView');

	return {
		run: function (viewManager) {
			viewManager.show(new ChoiceView({
				onChoiceVideo: function () {
					viewManager.show(new PrepareView({
						onPrepared: function (video) {
							viewManager.show(new ImportView({ video: video }));
						}
					}));
				},
				onChoicePlaylist: function () {
					viewManager.show(new PreparePlaylistView({
						onPrepared: function (playlist, url) {
							viewManager.show(new ImportPlaylistView({ 
								playlist: playlist,
								playlistUrl: url
							}));
						}
					}));
				}
			}));
		}
	};
});
