define(function (require) {
	var Backbone = require('Backbone');
	var Playlist = require('./../models/Playlist');
	var template = require('hbs!./../templates/CreateView');

	return Backbone.View.extend({
		template: template,

		events: {
			'submit .js-create-form': 'onCreate'
		},

		initialize: function () {
			this.error = null;
		},

		render: function () {
			this.$el.html(this.template({ error: this.error }));
			return this;
		},

		onCreate: function (e) {
			e.preventDefault();
			var self = this;
			var tracks = this.$('textarea[name=tracks]').val()
				.split(/\r?\n/)
				.map(function (s) { return s.trim(); })
				.filter(Boolean);

			var attrs = {
				title:  this.$('input[name=title]').val().trim(),
				artist: this.$('input[name=artist]').val().trim(),
				genre:  this.$('input[name=genre]').val().trim(),
				year:   parseInt(this.$('input[name=year]').val(), 10),
				tracks: tracks
			};

			var playlist = new Playlist();
			playlist.save(attrs, {
				success: function (model) {
					window.location.hash = '#/playlists/' + model.get('uid');
				},
				error: function (m, xhr) {
					self.error = 'Failed to create playlist: ' + xhr.status;
					self.render();
				}
			});
		}
	});
});
