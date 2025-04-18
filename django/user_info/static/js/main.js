"use strict"

$(window).on("load", function() {
$('.btn-forget').on('click',function(e){
    var inputField = $(this).closest('form').find('input[name="username"]');
    if(inputField.attr('required') && inputField.val()){
        // Allow the form to submit normally
        $('.error-message').remove();
        return true;
    }else{
        e.preventDefault();
        $('.error-message').remove();
        $('<small class="error-message">Please fill the field.</small>').insertAfter(inputField);
        return false;
    }
});
    
    $('.btn-tab-next').on('click',function(e){
        e.preventDefault();
        $('.nav-tabs .nav-item > .active').parent().next('li').find('a').trigger('click');
    });
    $('.custom-file input[type="file"]').on('change', function(){
        var filename = $(this).val().split('\\').pop();
        $(this).next().text(filename);
    });
});
