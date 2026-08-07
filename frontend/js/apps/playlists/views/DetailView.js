define(function (require) {
	var $ = require('jQuery');
	var Backbone = require('Backbone');
	var template = require('hbs!./../templates/DetailView');

	return Backbone.View.extend({
		template: template,

		events: {
			'submit .js-meta-form':    'onSaveMeta',
			'click .js-delete':        'onDelete',
			'submit .js-add-track':    'onAddTrack',
			'click .js-remove-track':  'onRemoveTrack'
		},

		initialize: function (options) {
			this.error = (options && options.error) || null;
			this.message = null;
		},

		render: function () {
			var data = this.model.toJSON();
			data.error = this.error;
			data.message = this.message;
			data.tracks = data.tracks || [];
			this.$el.html(this.template(data));
			return this;
		},

		onSaveMeta: function (e) {
			e.preventDefault();
			var self = this;
			var attrs = {
				title:  this.$('input[name=title]').val()  || null,
				artist: this.$('input[name=artist]').val() || null,
				genre:  this.$('input[name=genre]').val()  || null,
				year:   this.$('input[name=year]').val() ? parseInt(this.$('input[name=year]').val(), 10) : null
			};

			this.model.updateMeta(attrs).then(function (data) {
				self.model.set(data);
				self.message = 'Meta updated';
				self.render();
			}, function (xhr) {
				self.error = 'Failed to update meta: ' + xhr.status;
				self.render();
			});
		},

		onDelete: function (e) {
			e.preventDefault();
			if (!window.confirm('Delete this playlist?')) { return; }
			this.model.delete().then(function () {
				window.location.hash = '#/playlists';
			});
		},

		onAddTrack: function (e) {
			e.preventDefault();
			var self = this;
			var uid = this.$('input[name=new-track]').val().trim();
			if (!uid) { return; }
			this.model.updateTracks('insert', [uid]).then(function (data) {
				self.model.set(data);
				self.message = 'Track added';
				self.render();
			}, function (xhr) {
				self.error = 'Failed to add track: ' + xhr.status;
				self.render();
			});
		},

		onRemoveTrack: function (e) {
			e.preventDefault();
			var self = this;
			var uid = $(e.currentTarget).data('uid');
			this.model.updateTracks('remove', [String(uid)]).then(function (data) {
				self.model.set(data);
				self.message = 'Track removed';
				self.render();
			}, function (xhr) {
				self.error = 'Failed to remove track: ' + xhr.status;
				self.render();
			});
		}
	});
});
