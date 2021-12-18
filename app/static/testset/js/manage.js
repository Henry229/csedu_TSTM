var _id;

$(document).ready(function () {
    /**
     * Initial setup processing:
     *  Set checked attr on the first radio object
     *  Set the value to plan_id html hidden obj for Clone, Edit, Delete
     *  Rendering Testlet Detail span objects with checked testlet
     *  Disable <Save Items> button
     *  */
    $radio = $('input[name="r_tl"]');
    $radio.each(function () {
        $(this).prop('checked', true);
        return false;
    });
    $checked_radio = $('input[name="r_tl"]:checked');
    _id = $checked_radio.val();
    $('input[name="testset_id"]').val(_id);

    /**
     * Event Handler:
     *      Radio : $('input[name="r_tl"]') click
     * */
    $radio.click(function () {
        _id = $(this).val();
        $checked_radio = $(this);
        $('input[name="testset_id"]').val(_id);
    });
});

/**
 * function redirectTestsetCreate(): redirect to the page Create - for New, Edit
 * @param obj: button object
 * @param mode: 'edit' or 'clone' or other
 * @returns {boolean}
 */
function redirectTestsetCreate(obj, mode) {
    if (mode == null) {
        var location = $(obj).attr("value").toLowerCase();
    } else if ((mode == 'edit') || (mode == 'clone')) {
        var location = $(obj).attr("value").toLowerCase() + '/' + _id;
        if ($radio.length == 0) {
            alert('Please choose testset you want to update first.');
            return false;
        }
    }

    $('#clone_form').attr("method", "GET");
    $('#clone_form').attr("action", location);
    $('#clone_form').submit();
}

function loadingQuestons(){
    if($('input[name="r_tl"]:checked').length==0){
        alert('select the testset item');
        return false;
    }
    $.ajax({
        url: '/testset/manage/questions',
        method: 'GET',
        data: {'testset_id': $('input[name="r_tl"]:checked').val()},
        success: function (response) {
            debugger
        }
    });
}