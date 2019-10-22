$(document).ready(function () {
    $('#load').on('click', function (event) {
        event.preventDefault();
        $('#load i').show();
        $('#load').prop('disabled', true);
        $('#form-load').submit();
    });

    $('#checkout').click(function () {
        $('#items_imported > tbody > tr').filter(':has(:checkbox:checked)').each(function () {
            var $row = $(this),
                $selected_level = $('#level option:selected'),
                $selected_category = $('#select_category option:selected'),
                $selected_subcategory = $('#select_subcategory option:selected');

            // Field List > selected > subcategory rendering
            var options = document.getElementById("select_subcategory").innerHTML;
            var parentObjId = $row.find('.item_categories')[0].id;
            var childObjId = parentObjId.replace('category', 'subcategory');
            document.getElementById(childObjId).innerHTML = options;

            var $level = $row.find('.item_levels option');
            var $category = $row.find('.item_categories option');
            var $subcategory = $row.find('.item_subcategories option');

            $level.filter(function () {
                return this.value === $selected_level.val();
            }).prop("selected", "selected");
            $category.filter(function () {
                return this.value === $selected_category.val();
            }).prop("selected", "selected");
            $subcategory.filter(function () {
                return this.value === $selected_subcategory.val();
            }).prop("selected", "selected");
        });
    });

    $('#import').click(function () {
        $('.item_ids').prop("checked", true);
    });
});