define(function (require) {
	var $ = require('jQuery');
	var Backbone = require('Backbone');
	var template = require('hbs!./../templates/ImportView');

	return Backbone.View.extend({
		template: template,

		events: {
			'click .js-add-segment':    'onAddSegment',
			'click .js-remove-segment': 'onRemoveSegment',
			'click .js-use-timecode':   'onUseTimecode',
			'submit .js-import-form':   'onImport'
		},

		initialize: function (options) {
			this.video = options.video;
			this.segments = [];
			this.error = null;
			this.message = null;
			this.loading = false;
		},

		render: function () {
			var displaySegments = this.segments.map(function (s) {
				var out = {};
				Object.keys(s).forEach(function (k) {
					out[k] = (s[k] === null || s[k] === undefined) ? '' : s[k];
				});
				return out;
			});
			this.$el.html(this.template({
				video: this.video,
				segments: displaySegments,
				error: this.error,
				message: this.message,
				loading: this.loading
			}));
			return this;
		},

		_syncSegmentsFromDom: function () {
			this.segments = this._collectSegments();
		},

		onAddSegment: function (e) {
			e.preventDefault();
			this._syncSegmentsFromDom();
			this.segments.push({
				from_second: 0,
				to_second: 0,
				override_title: null,
				override_artist: null,
				override_album: null,
				override_year: null,
				override_genre: null,
				override_album_cover: null
			});
			this.render();
		},

		onRemoveSegment: function (e) {
			e.preventDefault();
			var idx = parseInt($(e.currentTarget).data('idx'), 10);
			this._syncSegmentsFromDom();
			this.segments.splice(idx, 1);
			this.render();
		},

		onUseTimecode: function (e) {
			e.preventDefault();
			var idx = parseInt($(e.currentTarget).data('idx'), 10);
			var timecodes = (this.video && this.video.timecodes) || [];
			var tc = timecodes[idx];
			if (!tc) { return; }

			var next = timecodes[idx + 1];
			var toSecond = next
				? next.seconds
				: (this.video.duration_seconds || tc.seconds);

			this._syncSegmentsFromDom();
			this.segments.push({
				from_second:          tc.seconds,
				to_second:            toSecond,
				override_title:       tc.label || null,
				override_artist:      null,
				override_album:       null,
				override_year:        null,
				override_genre:       null,
				override_album_cover: null
			});
			this.render();
		},

		_collectSegments: function () {
			return this.$('.js-segment').map(function () {
				var $s = $(this);
				return {
					from_second:          parseInt($s.find('[name=from_second]').val(), 10) || 0,
					to_second:            parseInt($s.find('[name=to_second]').val(), 10) || 0,
					override_title:       $s.find('[name=override_title]').val() || null,
					override_artist:      $s.find('[name=override_artist]').val() || null,
					override_album:       $s.find('[name=override_album]').val() || null,
					override_year:        $s.find('[name=override_year]').val() ? parseInt($s.find('[name=override_year]').val(), 10) : null,
					override_genre:       $s.find('[name=override_genre]').val() || null,
					override_album_cover: $s.find('[name=override_album_cover]').val() || null
				};
			}).get();
		},

		onImport: function (e) {
			e.preventDefault();
			var self = this;
			var segments = this._collectSegments();
			var body = {
				url:              this.video.url,
				override_title:   this.$('input[name=override_title]').val()  || null,
				override_artist:  this.$('input[name=override_artist]').val() || null,
				override_album:   this.$('input[name=override_album]').val()  || null,
				override_year:    this.$('input[name=override_year]').val() ? parseInt(this.$('input[name=override_year]').val(), 10) : null,
				override_genre:   this.$('input[name=override_genre]').val() || null,
				segments:         segments.length ? segments : null
			};

			this.loading = true;
			this.error = null;
			this.message = null;
			this.render();

			Backbone.ajax({
				url: '/api/yt/import',
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
