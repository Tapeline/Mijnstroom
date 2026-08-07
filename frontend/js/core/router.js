define(function(require) {
	var Backbone = require('Backbone');
	var viewManager = require('./viewManager');

	var Router = Backbone.Router.extend({
		routes: {
			'':                       'home',
			'/':                      'home',
			'tracks':                 'tracks',
			'/tracks':                'tracks',
			'tracks/:uid':            'trackDetail',
			'/tracks/:uid':           'trackDetail',
			'playlists':              'playlists',
			'/playlists':             'playlists',
			'playlists/new':          'playlistNew',
			'/playlists/new':         'playlistNew',
			'playlists/:uid':         'playlistDetail',
			'/playlists/:uid':        'playlistDetail',
			'yt':                     'yt',
			'/yt':                    'yt',
			'jobs':                   'jobs',
			'/jobs':                  'jobs',
			'jobs/:uid':              'jobDetail',
			'/jobs/:uid':             'jobDetail'
		},

		home: function () {
			require(['./../apps/home/app'], function (app) { app.run(viewManager); });
		},

		tracks: function () {
			require(['./../apps/tracks/app'], function (app) { app.run(viewManager); });
		},

		trackDetail: function (uid) {
			require(['./../apps/tracks/app'], function (app) { app.detail(viewManager, uid); });
		},

		playlists: function () {
			require(['./../apps/playlists/app'], function (app) { app.run(viewManager); });
		},

		playlistNew: function () {
			require(['./../apps/playlists/app'], function (app) { app.create(viewManager); });
		},

		playlistDetail: function (uid) {
			require(['./../apps/playlists/app'], function (app) { app.detail(viewManager, uid); });
		},

		yt: function () {
			require(['./../apps/yt/app'], function (app) { app.run(viewManager); });
		},

		jobs: function () {
			require(['./../apps/jobs/app'], function (app) { app.run(viewManager); });
		},

		jobDetail: function (uid) {
			require(['./../apps/jobs/app'], function (app) { app.detail(viewManager, uid); });
		}
	});

	return Router;
});
