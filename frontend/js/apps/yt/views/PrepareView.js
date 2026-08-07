define(function (require) {
	var Backbone = require('Backbone');
	var template = require('hbs!./../templates/PrepareView');

	return Backbone.View.extend({
		template: template,

		events: {
			'submit .js-prepare-form': 'onPrepare'
		},

		initialize: function (options) {
			this.onPrepared = options.onPrepared;
			this.error = null;
			this.loading = false;
		},

		render: function () {
			this.$el.html(this.template({
				error: this.error,
				loading: this.loading
			}));
			return this;
		},

		onPrepare: function (e) {
			e.preventDefault();
			var self = this;
			var url = this.$('input[name=url]').val().trim();
			if (!url) { return; }

			this.loading = true;
			this.error = null;
			this.render();

			Backbone.ajax({
				url: '/api/yt/prepare',
				method: 'POST',
				contentType: 'application/json',
				data: JSON.stringify({ url: url })
			}).then(function (video) {
				self.onPrepared(video);
			}, function (xhr) {
				self.loading = false;
				self.error = 'Prepare failed: ' + xhr.status;
				self.render();
			});
		}
	});
});
