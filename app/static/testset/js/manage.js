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

    $('#bindAdd').click(function(){
        if($('#bindingModal input[type="checkbox"]:checked').length==0){
            alert('please check the item');
            return false;
        }else{
            let itemIds = '';
            let questionNos = '';
            for(var i=0; i<$('#bindingModal input[type="checkbox"]:checked').length; i++){
                if(itemIds!='') itemIds += ',';
                itemIds += $($('#bindingModal input[type="checkbox"]:checked').get(i)).val();
                if(questionNos!='') questionNos += ',';
                questionNos += $($('#bindingModal input[type="checkbox"]:checked').get(i)).attr('data-no');
            }
            var data = {
                "testset_id": $('#testsets input[type="radio"]:checked').val(),
                "item_id": itemIds,
                "question_no": questionNos,
                "bind_id": $('#bindingModal select[name="bind_list"] > option').length + 1,
            };
            $.ajax({
                url: '/testset/manage/bind/add',
                method: 'GET',
                data: data,
                success: function (response) {
                    var option = $("<option>Bind "+($('#bindingModal select[name="bind_list"] > option').length + 1)+"</option>");
                    $('#bindingModal select[name="bind_list"]').append(option);
                }
                ,error: function(XMLHttpRequest, textStatus, errorThrown) {
                }
            });
            return false;
        }



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
        beforeSend: function () {
            $('#bindingModal ul').empty();
        },
        success: function (response) {
            for(var i=0; i<response.length; i++){
                var txt = $.trim($(response[i].html).find('div.qti-interaction').text().replaceAll('\n', ''))
                var item_id = response[i].item_id;
                var obj = '';
                obj += '<div style="height:30px">';
                obj += '<li class="d-flex">';
                obj += '<input type="checkbox" class="form-check-input" style="position:unset;margin-left:unset;margin-right:10px" data-no="'+(i+1)+'" value="'+item_id+'"><div class="d-inline-block" style="width:30px"><strong>'+(i+1)+'.</strong></div><span>'+txt.substr(0, 70) + '...' +'</span>';
                //obj += '<div class="float-right" style="width:70px;height:30px"><span></span><span></span></div>';
                obj += '</li>';
                obj += '</div>';
                $('#bindingModal ul').append(obj);
            }
        }
    });
}