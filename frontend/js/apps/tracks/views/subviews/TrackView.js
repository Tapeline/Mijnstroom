define(function (require) {
	var Backbone = require('Backbone');
	var template = require('hbs!./../../templates/TrackView');

	return Backbone.View.extend({
		tagName: 'div',
		className: 'mdl-card mdl-shadow--2dp mdl-cell mdl-cell--4-col',

		events: {
			'click .js-delete': 'onDelete'
		},

		template: template,

		render: function () {
			this.$el.html(this.template(this.model.toJSON()));
			return this;
		},

		onDelete: function (e) {
			e.preventDefault();
			if (!window.confirm('Delete this track?')) { return; }
			var self = this;
			this.model.delete().then(function () {
				self.$el.remove();
			});
		}
	});
});
