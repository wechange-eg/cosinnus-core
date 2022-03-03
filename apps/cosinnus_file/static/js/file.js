function init_select_all(selector, context) {
  $(selector).change(function() {
    if ($(selector).is(':checked')) {
      $(context).find(':checkbox[name=select]').prop("checked", true);
    } else {
      $(context).find(':checkbox[name=select]').prop("checked", false);
    }
  });
}