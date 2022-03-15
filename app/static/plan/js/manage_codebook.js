$("#status").hide();

$('#select_subject').on('change', function(){
    $(this).parent().find('p').remove();
    if($(this).val()!='0'){
        $(this).parent().append('<p>'+$(this).val()+'</p>');
    }
});

$('.code_type').on('change', function () {
    var $updateCodeObj = $(this).closest('tr').find("input.update_code");
    var $additionalInfoObj = $(this).closest('tr').find("textarea.additional_info");
    var code_id = $(this).children("option:selected").val();
    if (code_id == 0) {
        reset_val();
    } else {
        getCodebookInfo(code_id, $updateCodeObj, $additionalInfoObj);
    }
});

$('.max-score-icon').on('click', function () {
    var $codeObj = $(this).closest('tr').find("select.code_type");
    var $codeTextObj = $(this).closest('tr').find("input.max_score");
    var code_id = $codeObj.children("option:selected").val();
    var code_value = $codeTextObj.val();

    if (code_value == null) {
        alert('Please enter max score value first.');
        return;
    }
    if (code_id == 0) {
        alert('Please select code from the list first.');
    } else {
        updateCodebook($codeObj, $codeTextObj, code_id, code_value, 'max_score');
    }
});

$('.subject-order-icon').on('click', function () {
    var $codeObj = $(this).closest('tr').find("select.code_type");
    var $codeTextObj = $(this).closest('tr').find("input.subject_order");
    var code_id = $codeObj.children("option:selected").val();
    var code_value = $codeTextObj.val();

    if (code_value == null) {
        alert('Please enter subject order value first.');
        return;
    }
    if (code_id == 0) {
        alert('Please select code from the list first.');
    } else {
        updateCodebook($codeObj, $codeTextObj, code_id, code_value, 'subject_order');
    }
});

$('.branch-state-icon').on('click', function () {
    var $codeObj = $(this).closest('tr').find("select.code_type");
    var $codeTextObj = $(this).closest('tr').find("select.branch_state");
    var code_id = $codeObj.children("option:selected").val();
    var code_value = $codeTextObj.children("option:selected").val();

    if (code_value == null) {
        alert('Please select branch state from the list first.');
        return;
    }
    if (code_id == 0) {
        alert('Please select code from the list first.');
    } else {
        updateCodebook($codeObj, $codeTextObj, code_id, code_value, 'branch_state');
    }
});

$('.additional-info-icon').on('click', function () {
    var $codeObj = $(this).closest('tr').find("select.code_type");
    var $codeTextObj = $(this).closest('tr').find("textarea.additional_info");
    var code_id = $codeObj.children("option:selected").val();
    var code_value = $codeTextObj.val();

    if (code_value == 0) {
        alert('Please type the value to update.');
        return;
    }
    if (code_id == 0) {
        alert('Please select code from the list first.');
    } else {
        updateCodebook($codeObj, $codeTextObj, code_id, code_value, 'additional_info');
    }
});

$('.update-icon').on('click', function () {
    var $codeObj = $(this).closest('tr').find("select.code_type");
    var $codeTextObj = $(this).closest('tr').find("input.update_code");
    var code_id = $codeObj.children("option:selected").val();
    var code_value = $codeTextObj.val();

    if (code_value == 0) {
        alert('Please type the value to update.');
        return;
    }
    if (code_id == 0) {
        alert('Please select code from the list first.');
    } else {
        updateCodebook($codeObj, $codeTextObj, code_id, code_value, 'code_name');
    }
});

$('.add-icon').on('click', function () {
    var $codeObj = $(this).closest('tr').find("select.code_type");
    var $codeTextObj = $(this).closest('tr').find("input.add_code");
    var code_value = $codeTextObj.val();
    if (code_value == 0) {
        alert('Please type the value to add.');
        return;
    }

    var $parentcodeObj = null;
    var code_type = $codeObj.attr("id");
    if (code_type == 'select_category')
        $parentcodeObj = $('#select_subject');
    else if (code_type == 'select_subcategory')
        $parentcodeObj = $('#select_category');
    else if (code_type == 'select_level')
        $parentcodeObj = $('#select_test_type');
    else if (code_type == 'select_criteria')
        $parentcodeObj = $('#select_test_type');

    if ($parentcodeObj == null)
        var code_id = null;
    else
        var code_id = $parentcodeObj.children("option:selected").val();

    if (code_id == 0) {
        alert('Please select parent code from the list first to add child code.');
    } else {
        addCodebook($codeObj, $codeTextObj, code_id, code_type.substr(7), code_value);
    }
});

function getCodebookInfo(code_id, updateCodeObj, additionalInfoObj) {
    var data = {
        'code_id': code_id
    };

    $.ajax({
        url: '/api/get_codebook_info/',
        method: 'GET',
        data: data,
        beforeSend: function () {
            updateCodeObj.val('');
            additionalInfoObj.val('');
            updateCodeObj.attr('disabled', 'disabled');
            additionalInfoObj.attr('disabled', 'disabled');
        },
        complete: function () {
            updateCodeObj.removeAttr('disabled');
            additionalInfoObj.removeAttr('disabled');
        },
        success: function (response) {
            updateCodeObj.val(response.code_name);
            if (response.additional_info.length!=0)
                additionalInfoObj.val(JSON.stringify(response.additional_info));
            else
                additionalInfoObj.val('');
        }
    });
}


function updateCodebook(selectObj, inputObj, code_id, code_value, code_value_field) {
    var data = {
        'code_id': code_id,
        'code_value': code_value,
        'code_value_field': code_value_field
    };

    $.ajax({
        url: '/api/update_codebook/',
        method: 'PUT',
        data: data,
        beforeSend: function () {
            selectObj.attr('disabled', 'disabled');
            inputObj.attr('disabled', 'disabled');
            selectObj.empty();
        },
        complete: function () {
            selectObj.removeAttr('disabled');
            inputObj.removeAttr('disabled');
            reset_val();
        },
        error: function(xhr, status, error) {
            if (code_value_field=='additional_info') {
                var e = JSON.parse(xhr.responseText);
                e_msg = e.result + ' [' + e.type + '] : ' + e.message;
            } else
                e_msg = xhr.responseText;
            console.log(e_msg);
            $("#status").show();
            $("#status").html(e_msg).fadeOut(9000, function () {
                $(this).hide();
            });
        },
        success: function (response) {
            selectObj.empty();
            inputObj.val('');
            response.data.child.forEach(function (item) {
                selectObj.append(
                    $('<option>', {
                        value: item[0],
                        text: item[1]
                    })
                );
            });
            $("#status").show();
            $("#status").html(response.data.message).fadeOut(3000, function () {
                $(this).hide();
            });
        }
    });
}

function addCodebook(selectObj, inputObj, code_id, code_type, code_value) {
    var data = {
        'parent_code_id': code_id,
        'code_type': code_type,
        'code_value': code_value
    };

    $.ajax({
        url: '/api/add_codebook/',
        method: 'POST',
        data: data,
        beforeSend: function () {
            selectObj.attr('disabled', 'disabled');
            inputObj.attr('disabled', 'disabled');
            selectObj.empty();
        },
        complete: function () {
            selectObj.removeAttr('disabled');
            inputObj.removeAttr('disabled');
            reset_val();
        },
        success: function (response) {
            response.forEach(function (item) {
                selectObj.append(
                    $('<option>', {
                        value: item[0],
                        text: item[1]
                    })
                );
            });
            $("#status").show();
            $("#status").html("Codebook added successfully").fadeOut(3000, function () {
                $(this).hide();
            });
        }
    });
}

function reset_val() {
        $(".update_code").val('');
        $(".additional_info").val('');
        $(".branch_state").val('');
        $(".max_score").val('');
        $(".subject_order").val('');
}