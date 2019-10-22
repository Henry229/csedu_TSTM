$(document).ready(function () {
    $('#selecctall_active').click(function () {
        if (this.checked) {
            $('.item_actives').each(function () {
                $(this).prop('checked', true);
            });
        } else {
            $('.item_actives').each(function () {
                $(this).prop('checked', false);
            });
        }
    });

    $('.item_actives').click(function () {
        if (!this.checked) {
            $('#selecctall_active').prop('checked', false);
        }
    });

    $('#reverse_active').click(function () {
        $('.item_actives').each(function () {
            var checked = $(this).prop('checked')
            if (checked) {
                $(this).prop('checked', false);
            } else {
                $(this).prop('checked', true);
            }
        });
    });

    $('#checkout').click(function () {
        $('#items_edit > tbody > tr').filter(':has(:checkbox.item_checkbox:checked)').each(function () {
            var $row = $(this),
                $selected_grade = $('#select_grade2 option:selected'),
                $selected_subject = $('#select_subject2 option:selected'),
                $selected_level = $('#select_level2 option:selected'),
                $selected_category = $('#select_category2 option:selected'),
                $selected_subcategory = $('#select_subcategory2 option:selected'),
                $selected_active = $('#select_active2');

            // Field List > selected > subcategory rendering
            var options = document.getElementById("select_subcategory2").innerHTML;
            var parentObjId = $row.find('.item_categories')[0].id;
            var childObjId = parentObjId.replace('category', 'subcategory');
            document.getElementById(childObjId).innerHTML = options;

            var $grade = $row.find('.item_grade option');
            var $subject = $row.find('.item_subjects option');
            var $level = $row.find('.item_levels option');
            var $category = $row.find('.item_categories option');
            var $subcategory = $row.find('.item_subcategories option');
            var $active = $row.find('.item_actives');

            if ($selected_grade.val() !== "0") {
                $grade.filter(function () {
                    return this.value === $selected_grade.val();
                }).prop("selected", "selected");
            }
            if ($selected_subject.val() !== "0") {
                $subject.filter(function () {
                    return this.value === $selected_subject.val();
                }).prop("selected", "selected");
            }
            if ($selected_level.val() !== "0") {
                $level.filter(function () {
                    return this.value === $selected_level.val();
                }).prop("selected", "selected");
            }
            if ($selected_category.val() !== "0") {
                $category.filter(function () {
                    return this.value === $selected_category.val();
                }).prop("selected", "selected");
            }
            if ($selected_subcategory.val() !== "0") {
                $subcategory.filter(function () {
                    return this.value === $selected_subcategory.val();
                }).prop("selected", "selected");
            }
            if ($selected_active.val() !== "0") {
                $active.val($selected_active.val());
            }
        });
    });

    $('#save').click(function () {
        $('.item_ids').prop("checked", true);
    });
});

function updateItemExplanation() {
    $('#extended_edit_form').submit();
}

function invokeItemExplanation(obj) {
    var url = $(obj).attr("value");
    $.get(url, function (data) {
        $('#dataModal .modal-content').html(data);
        $('#dataModal').modal();
    });
}
