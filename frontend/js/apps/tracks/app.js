define(function (require) {
	var TracksCollection = require('./collections/TracksCollection');
	var MainView = require('./views/MainView');

	return {
		run: function(viewManager) {
			var tracksCollection = new TracksCollection();
			tracksCollection.fetch({
				success: function (tracks) {
					var view = new MainView({collection: tracks});
					viewManager.show(view);
				}
			});
		}
	};
});