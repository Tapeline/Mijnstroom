define(function (require) {
	var HomeView = require('./views/HomeView');

	return {
		run: function (viewManager) {
			viewManager.show(new HomeView());
		}
	};
});
