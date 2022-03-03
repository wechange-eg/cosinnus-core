function validURL(str) {
    var pattern = new RegExp('^(https?:\\/\\/)?'+ // protocol
        '((([a-z\\d]([a-z\\d-]*[a-z\\d])*)\\.)+[a-z]{2,}|'+ // domain name
        '((\\d{1,3}\\.){3}\\d{1,3}))'+ // OR ip (v4) address
        '(\\:\\d+)?(\\/[-a-z\\d%_.~+]*)*'+ // port and path
        '(\\?[;&a-z\\d%_.~+=-]*)?'+ // query string
        '(\\#[-a-z\\d_]*)?$','i'); // fragment locator
    return !!pattern.test(str);
}

function init_file_url_form() {
    // on url input change, grab metadata and fill inputs if they are empty
    $('#id_url').on("input paste", function(){
        url = $(this).val();
        if (validURL(url)) {
            $('#fileUrlSpinner').show();
            $.get('/api/v1/common/get-metadata/?url=' + url , function( data ) {
                var titlefield = $('#id_title');
                if (data.title && titlefield.val().length == 0) {
                    titlefield.val(data.title);
                }
                if (data.description && inited_simplemde.value().length == 0) {
                    inited_simplemde.value(data.description);
                }
            }).always(function() {
                $('#fileUrlSpinner').hide();
            });
        }
    });
    
    // enter presses on fields submit the form
    $('#id_url, #id_title').keypress(function (e) {
        if (e.which == 13) {
            $('form#file_url_upload_form').submit();
            return false;
        }
    });
}

$(function(){
    $('#add-url-modal').on('shown.bs.modal', function (e) {
        $('#id_url').focus();
    });
    
    // clear form on modal close
    $('#add-url-modal').on('hidden.bs.modal', function (e) {
        $('#id_url').val('');
        $('#id_title').val('');
        inited_simplemde.value('');
    });
    
    init_file_url_form();
});
