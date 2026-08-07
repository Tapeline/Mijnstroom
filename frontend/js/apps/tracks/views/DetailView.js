define(function (require) {
	var Backbone = require('Backbone');
	var template = require('hbs!./../templates/DetailView');

	return Backbone.View.extend({
		template: template,

		events: {
			'click .js-delete': 'onDelete'
		},

		initialize: function (options) {
			this.error = (options && options.error) || null;
		},

		render: function () {
			var data = this.model.toJSON();
			data.error = this.error;
			this.$el.html(this.template(data));
			return this;
		},

		onDelete: function (e) {
			e.preventDefault();
			if (!window.confirm('Delete this track?')) { return; }
			this.model.delete().then(function () {
				window.location.hash = '#/tracks';
			});
		}
	});
});
