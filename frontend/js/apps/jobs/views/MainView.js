define(function (require) {
	var Backbone = require('Backbone');
	var template = require('hbs!./../templates/MainView');

	return Backbone.View.extend({
		template: template,

		initialize: function (options) {
			this.error = (options && options.error) || null;
		},

		render: function () {
			var jobs = this.collection.toJSON().map(function (j, i) {
				j.__index = i;
				return j;
			});
			this.$el.html(this.template({ jobs: jobs, error: this.error }));
			return this;
		}
	});
});
