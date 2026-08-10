define(function (require) {
	var $ = require('jQuery');
	var Backbone = require('Backbone');
	var template = require('hbs!./../templates/ImportPlaylistView');

	return Backbone.View.extend({
		template: template,

		events: {
			'submit .js-import-form': 'onImport'
		},

		initialize: function (options) {
			this.playlist = options.playlist;
			this.playlistUrl = options.playlistUrl;
			this.videos = (this.playlist.entries || []).map(function (entry) {
				return {
					video_id: entry.id,
					title: entry.title,
					channel: entry.channel,
					duration_seconds: entry.duration_seconds,
					thumbnail_url: entry.thumbnail_url,
					url: entry.url,
					enabled: true,
					override_title: '',
					override_artist: ''
				};
			});
			this.error = null;
			this.message = null;
			this.loading = false;
		},

		render: function () {
			this.$el.html(this.template({
				playlist: this.playlist,
				videos: this.videos,
				error: this.error,
				message: this.message,
				loading: this.loading
			}));
			return this;
		},

		_collectVideos: function () {
			var self = this;
			return this.$('.js-video').map(function () {
				var $v = $(this);
				var idx = parseInt($v.data('idx'), 10);
				var video = self.videos[idx];
				return {
					video_id: video.video_id,
					enabled: $v.find('.js-video-enabled').is(':checked'),
					override_title: $v.find('[name=override_title]').val() || null,
					override_artist: $v.find('[name=override_artist]').val() || null,
					override_album: null,
					override_year: null,
					override_genre: null
				};
			}).get();
		},

		onImport: function (e) {
			e.preventDefault();
			var self = this;
			var videos = this._collectVideos();

			var body = {
				url: this.playlistUrl,
				override_artist: this.$('input[name=override_artist]').val() || null,
				override_album: this.$('input[name=override_album]').val() || null,
				override_year: this.$('input[name=override_year]').val() ? parseInt(this.$('input[name=override_year]').val(), 10) : null,
				override_genre: this.$('input[name=override_genre]').val() || null,
				videos: videos
			};

			this.loading = true;
			this.error = null;
			this.message = null;
			this.render();

			Backbone.ajax({
				url: '/api/yt/playlist/import',
				method: 'POST',
				contentType: 'application/json',
				data: JSON.stringify(body)
			}).then(function (res) {
				self.loading = false;
				self.message = 'Import queued.' + (res && res.job_uid ? ' Job UID: ' + res.job_uid : '');
				self.render();
			}, function (xhr) {
				self.loading = false;
				self.error = 'Import failed: ' + xhr.status;
				self.render();
			});
		}
	});
});
