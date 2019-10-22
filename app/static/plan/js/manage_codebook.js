$("#status").hide();

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
        updateCodebook($codeObj, $codeTextObj, code_id, code_value);
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

function updateCodebook(selectObj, inputObj, code_id, code_value) {
    var data = {
        'code_id': code_id,
        'code_value': code_value
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
            inputObj.val('');
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
            $("#status").html("Codebook updated successfully").fadeOut(3000, function () {
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
            inputObj.val('');
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