define(function (require) {
	var Backbone = require('Backbone');
	var template = require('hbs!./../templates/HomeView');

	return Backbone.View.extend({
		template: template,

		render: function () {
			this.$el.html(this.template());
			return this;
		}
	});
});
