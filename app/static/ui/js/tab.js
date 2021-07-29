$(function(){
    $('#tab1').click(function(){
        $('#tab1-contents').removeAttr('hidden');
        $('#tab2-contents').attr('hidden', true);
    });
    $('#tab2').click(function(){
        $('#tab1-contents').attr('hidden', true);
        $('#tab2-contents').removeAttr('hidden');
    });
});