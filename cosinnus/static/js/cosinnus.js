(function ($, window, document) {
    window.Cosinnus = {
        init: function(base_url) {
            this.base_url = cosinnus_base_url;
            $.ajaxSetup({
                // From the Django documentation:
                // https://docs.djangoproject.com/en/1.6/ref/contrib/csrf/
                crossDomain: false,
                beforeSend: function(xhr, settings) {
                    if (!Cosinnus.csrfSafeMethod(settings.type)) {
                        xhr.setRequestHeader("X-CSRFToken", Cosinnus.getCookie('csrftoken'));
                    }
                }
            });
            return this;
        },
        getCookie: function(name) {
            // From the Django documentation:
            // https://docs.djangoproject.com/en/1.6/ref/contrib/csrf/
            var cookieValue = null;
            if (document.cookie && document.cookie !== '') {
                var cookies = document.cookie.split(';');
                for (var i = 0; i < cookies.length; i++) {
                    var cookie = jQuery.trim(cookies[i]);
                    if (cookie.substring(0, name.length + 1) == (name + '=')) {
                        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                        break;
                    }
                }
            }
            return cookieValue;
        },
        csrfSafeMethod: function(method) {
            // From the Django documentation:
            // https://docs.djangoproject.com/en/1.6/ref/contrib/csrf/
            // these HTTP methods do not require CSRF protection
            return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
        }
    };
    $.fn.cosinnus = Cosinnus.init(cosinnus_base_url);
}(jQuery, this, this.document));

// Dashboard: activate links
$('.js-todo-link').on('click', function(e) {
    e.preventDefault();
    e.stopPropagation();
    location.href = location.pathname + 'todo/';
});
