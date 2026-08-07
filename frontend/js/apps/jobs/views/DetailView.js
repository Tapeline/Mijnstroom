define(function (require) {
	var Backbone = require('Backbone');
	var template = require('hbs!./../templates/DetailView');

	return Backbone.View.extend({
		template: template,

		events: {
			'click .js-refresh': 'onRefresh'
		},

		initialize: function (options) {
			this.uid = options.uid;
			this.error = options.error || null;
		},

		render: function () {
			var data = this.model.toJSON();
			data.uid = this.uid;
			data.error = this.error;
			data.log = data.log || [];
			this.$el.html(this.template(data));
			return this;
		},

		onRefresh: function (e) {
			e.preventDefault();
			var self = this;
			this.model.fetch({
				success: function () { self.error = null; self.render(); },
				error: function () { self.error = 'Refresh failed'; self.render(); }
			});
		}
	});
});
