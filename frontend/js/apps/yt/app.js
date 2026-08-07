define(function (require) {
	var Backbone = require('Backbone');
	var PrepareView = require('./views/PrepareView');
	var ImportView = require('./views/ImportView');

	return {
		run: function (viewManager) {
			viewManager.show(new PrepareView({
				onPrepared: function (video) {
					viewManager.show(new ImportView({ video: video }));
				}
			}));
		}
	};
});
