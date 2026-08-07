define(function (require) {
	var JobsCollection = require('./collections/JobsCollection');
	var Job = require('./models/Job');
	var MainView = require('./views/MainView');
	var DetailView = require('./views/DetailView');

	return {
		run: function (viewManager) {
			var jobs = new JobsCollection();
			jobs.fetch({
				success: function () {
					viewManager.show(new MainView({ collection: jobs }));
				},
				error: function () {
					viewManager.show(new MainView({
						collection: new JobsCollection(),
						error: 'Failed to load jobs'
					}));
				}
			});
		},

		detail: function (viewManager, uid) {
			var job = new Job({ uid: uid });
			job.fetch({
				success: function () {
					viewManager.show(new DetailView({ model: job, uid: uid }));
				},
				error: function () {
					viewManager.show(new DetailView({
						model: new Job({ uid: uid }),
						uid: uid,
						error: 'Failed to load job'
					}));
				}
			});
		}
	};
});
