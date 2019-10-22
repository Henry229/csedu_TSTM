/*
*  Revealing Module Pattern
*  Reference: https://scotch.io/bar-talk/4-javascript-design-patterns-you-should-know
*/

var TestsetStageTable = (function () {
    var _stageDepth;
    var _stageData;
    var _stageDataAdd;
    var _stageDataOrgStr;
    var _wrapper;
    var _table;
    var _tableHead;
    var _tableBody;
    var _styles;
    var _testlets;
    var _rowCallbacks;
    var _mode = 'edit';
    var _lastRect; // object {left:0, top:0};

    /**
     * 하나의 row 를 생성하는 클라스.
     *
     * @param context 전체 table 에서 현재의 row 를 생성하기까지 정보를 저장하고 있다가 전달해 준다.
     * @param callbacks add, delete 등의 기능을 실제로 해 주는 callbacks
     * @constructor
     */
    function StageRow(context, callbacks) {
        this.addRowStartCallback = callbacks.addRowStart;
        this.addRowConfirmCallback = callbacks.addRowConfirm;
        this.addRowCancelCallback = callbacks.addRowCancel;
        this.deleteRowCallback = callbacks.deleteRow;
        this.context = context;
        this.stages = {};
        /**
         * 각 stage(depth) 별 array 의 마지막인지를 저장하고 있다.
         */
        this.isLastInStage = {};
        /**
         * _stageData 에서 현재 row 에 해당하는 각 stage(depth) 별 index of array
         */
        this.rowInfo = {};

        this.maxDepth = 0;

        /**
         * context 에 있는 isLastInStage, rowInfo 를 복사해서 self 에 저장한다.
         */
        for (var s in context.isLastInStage) {
            if (!context.isLastInStage.hasOwnProperty(s)) continue;
            this.isLastInStage[s] = context.isLastInStage[s];
        }
        for (s in context.rowInfo) {
            if (!context.rowInfo.hasOwnProperty(s)) continue;
            this.rowInfo[s] = context.rowInfo[s];
        }
        this.setStage = function (depth, stage) {
            this.stages[depth] = stage;
            if (depth > this.maxDepth)
                this.maxDepth = depth;
        };
        this.setRowInfo = function (depth, index) {
            this.rowInfo[depth] = index;
            context.rowInfo[depth] = index;
        };
        this.setIsLastInStage = function (depth, is_last) {
            this.isLastInStage[depth] = is_last;
            context.isLastInStage[depth] = is_last;
        };
        /**
         * stage select 를 생성한다.
         * @returns {*|jQuery.fn.init|jQuery|HTMLElement}
         */
        this.buildSelect = function () {
            var select = $('<select>');
            for (var i = 0; i < _testlets.length; i++) {
                var option = $('<option>');
                var testlet = _testlets[i];
                option.html(testlet[1]);
                option.val(testlet[0]);
                select.append(option);
            }
            return select;
        };

        /**
         * 저장된 정보를 바탕으로 row 용 <tr></tr> 을 생성한다.
         * @returns {*|jQuery.fn.init|jQuery|HTMLElement}
         */
        this.buildRow = function () {
            var self = this;
            var condition, testlets, trash, del_ok, del_cancel;

            var row_mode = self.stages[self.maxDepth].mode || 'edit'; //row_mode = 'edit' or 'new'
            var tr = $('<tr>');
            tr.addClass(row_mode);

            /**
             * 각 stage 별 condition, name 을 생성한다.
             */
            var name_td, condition_td, is_stage1;
            var is_first = true; // 각 row 에서 활성화된 첫 column
            for (var i = 0; i < self.maxDepth; i++) {
                is_stage1 = (i === 0);
                var depth = i + 1;

                if (!is_stage1) {
                    condition_td = $('<td class="condition">');
                    tr.append(condition_td);
                }
                name_td = $('<td class="name">');
                tr.append(name_td);
                if (this.stages.hasOwnProperty(depth)) {
                    if (!is_stage1) {
                        condition = $('<input>');
                        condition.val(self.stages[depth].condition);
                        condition.data('depth', depth);
                        condition.on('blur', function () {
                            var d = $(this).data('depth');
                            self.stages[d].condition = parseInt(this.value);
                        });
                        condition_td.append(condition);
                        if (is_first) {
                            condition_td.addClass('first');
                            is_first = false;
                        }
                    }
                    testlets = this.buildSelect();
                    testlets.val(self.stages[depth].id);
                    testlets.data('depth', depth);
                    testlets.on('change', function () {
                        var d = $(this).data('depth');
                        self.stages[d].id = parseInt($(this).val());
                        self.stages[d].name = $(this).find('option:selected').text();
                    });
                    name_td.append(testlets);
                    if (is_first) {
                        name_td.addClass('first');
                        is_first = false;
                    }
                    if (row_mode === 'edit') {
                        trash = $('<i class="fas fa-trash-alt trash"></i>');
                        trash.data('name_td', name_td);
                        trash.on('click', function () {
                            var n = $(this).data('name_td');
                            n.addClass("delete-mode");
                            _table.addClass('delete-mode');
                        });
                        name_td.append(trash);
                        del_ok = $('<a class="badge badge-danger del-ok">Delete</a>');
                        del_ok.data('depth', depth);
                        del_ok.on('click', function () {
                            var d = parseInt($(this).data('depth'));
                            self.deleteRowCallback(d, self.rowInfo, self.maxDepth);
                        });
                        name_td.append(del_ok);
                        del_cancel = $('<a class="badge badge-secondary del-cancel">Cancel</a>');
                        del_cancel.data('name_td', name_td);
                        del_cancel.on('click', function () {
                            var n = $(this).data('name_td');
                            n.removeClass("delete-mode");
                            _table.removeClass('delete-mode');
                        });
                        name_td.append(del_cancel);
                    }
                } else {
                    if (!is_stage1) {
                        condition_td.addClass('blank');
                    }
                    name_td.addClass('blank');
                }
            }

            /**
             * 마지막 column 의 기능을 추가한다.
             * new, edit 모드가 있다.
             * @type {*|jQuery.fn.init|jQuery|HTMLElement}
             */
            var add_td = $('<td class="add">');
            if (self.stages[self.maxDepth].mode && self.stages[self.maxDepth].mode === 'new') {
                var add_confirm = $('<a class="badge badge-primary">Confirm</a>');
                add_confirm.on('click', function () {
                    self.addRowConfirmCallback();
                });
                add_td.append(add_confirm);
                var add_cancel = $('<a class="badge badge-secondary">Cancel</a>');
                add_cancel.on('click', function () {
                    self.addRowCancelCallback();
                });
                add_td.append(add_cancel);
            } else {
                var add_select = $('<select class="add-stage">');
                var option = $('<option>');
                add_select.append(option);
                option.text('Add stage');
                for (var j = 0; j < self.maxDepth; j++) {
                    var d = j + 1;
                    var add_ok = true;
                    for (var k = d + 1; k <= self.maxDepth; k++) {
                        if (!self.isLastInStage[k]) {
                            add_ok = false;
                            break;
                        }
                    }
                    if (d !== 1 && add_ok) {
                        option = $('<option>');
                        option.val(d);
                        option.text('Stage ' + d);
                        add_select.append(option);
                    }
                }
                add_select.on('change', function () {
                    if ($(this).val() === '')
                        self.addRowCancelCallback();
                    else {
                        var d = parseInt($(this).val());
                        self.addRowStartCallback(d, self.rowInfo, self.maxDepth)
                    }
                });
                add_td.append(add_select);
            }
            tr.append(add_td);
            return tr;
        }
    }

    var setData = function (data) {
        data = data || [];
        if (typeof data === 'string')
            _stageData = JSON.parse(data);
        else
            _stageData = data;
        _stageDataOrgStr = JSON.stringify(_stageData);
    };
    var getData = function () {
        return {'stage_depth': _stageDepth, 'data': _stageData};
    };
    var saveLastScrollRect = function () {
        var container = $('.dataTables_scrollBody');
        if (container.length === 0) return;
        container = container[0];
        _lastRect = {left: container.scrollLeft, top: container.scrollTop};
    };
    /**
     * 자동으로 마지막 위치로 스크롤을 하기위해.
     * container = $('.dataTables_scrollBody')[0]
     *        Datatable 이  scroll 을 생성하는 경우 생기는 container
     * _lastRect : 마지막 위치를 기억하고 싶은 경우 사용한다.
     *           _lastRect = {left: container.scrollLeft, top: container.scrollTop}
     * first_element = $('.new .first')
     *        Add mode 인 경우 새로 추가된 row 로 자동 이동한다.
     */
    var scrollToScrollRect = function () {
        var left, top;
        var container = $('.dataTables_scrollBody');
        if (container.length === 0) return;
        container = container[0];
        if (_lastRect) {
            left = _lastRect.left;
            top = _lastRect.top;
            _lastRect = null;
        } else {
            var first_element = $('.new .first');
            if (first_element.length === 0) return;
            first_element = first_element[0];
            var rect = first_element.getBoundingClientRect();
            var rect_c = container.getBoundingClientRect();
            left = rect.left - rect_c.left - 10;
            if (left < 0) left = 0;
            top = rect.top - rect_c.top - 40;
            if (top < 0) top = 0;
        }
        container.scrollTo(left, top);
    };
    /**
     * Callback function : row add 를 시작한다.
     * @param depth
     * @param row_info
     * @param max_depth
     * @private
     */
    var _addRowStart = function (depth, row_info, max_depth) {
        // Copy stageData
        _stageDataAdd = JSON.parse(JSON.stringify(_stageData));
        _mode = 'add';

        var new_stage = {
            "name": "",
            "id": 0,
            "condition": 0,
            "mode": "new"
        };
        for (var i = max_depth - 1; i >= depth; i--) {
            new_stage = {
                "name": "",
                "id": 0,
                "condition": 0,
                "next": [new_stage]
            }
        }
        // 새로 만드는 경우
        if (depth === 1) {
            _stageDataAdd = [new_stage];
        } else {
            var stage = _stageDataAdd[0].next;
            for (i = 1; i < depth - 1; i++) {
                stage = stage[row_info[i + 1]].next;
            }
            stage.splice(row_info[depth] + 1, 0, new_stage);
        }
        _draw(true);
        _table.addClass('add-mode');
    };
    /**
     * Callback function : row add 를 저장한다.
     * @private
     */
    var _addRowConfirm = function () {
        function deleteMode(stage_data) {
            if (stage_data.next) {
                for (var i = 0; i < stage_data.next.length; i++) {
                    deleteMode(stage_data.next[i]);
                }
            } else {
                if (stage_data.mode)
                    delete stage_data.mode;
            }
        }

        var stage_data = _stageDataAdd[0];
        deleteMode(stage_data);
        _stageData = _stageDataAdd;
        _stageDataAdd = [];
        _mode = 'edit';
        saveLastScrollRect();
        _draw();
    };
    /**
     * Callback function : row add 를 취소한다.
     * @private
     */
    var _addRowCancel = function () {
        _stageDataAdd = [];
        _mode = 'edit';
        saveLastScrollRect();
        _draw();
    };
    /**
     * Callback function : row 를 삭제한다.
     * @param depth
     * @param row_info
     * @param max_depth
     * @private
     */
    var _deleteRow = function (depth, row_info, max_depth) {
        if (depth === 1) {
            _stageData = [];
        } else {
            var stage = _stageData[0].next;
            for (var i = 1; i < depth - 1; i++) {
                stage = stage[row_info[i + 1]].next;
            }
            stage.splice(row_info[depth], 1);
        }

        if (_stageData.length === 0)
            _addRowStart(1, row_info, max_depth);
        else
            _draw(true);
    };

    /**
     *
     * @param wrapper string : selector ex) '.wrapper', '#wrapper'
     * @param testset_data object : json string or object
     * @param options object with
     *      + testlets: list of [(testlet.id, testlet.name)] for select
     *         ex) [[1, 'testlet001'], [2, 'testlet002'],.... ]
     *        + styles : class names
     *        ex) { tableClass: 'table'}
     *        See _drawXXXX functions for available options.
     */
    var init = function (wrapper, testset_data, options) {
        _wrapper = $(wrapper);
        _styles = options.styles || {};
        _testlets = options.testlets || {};
        _rowCallbacks = {
            'addRowStart': _addRowStart,
            'addRowConfirm': _addRowConfirm,
            'addRowCancel': _addRowCancel,
            'deleteRow': _deleteRow
        };

        _stageDepth = testset_data.stage_depth;
        setData(testset_data.data);

        /* Draw stage table */
        if (_stageData.length === 0)
            _addRowStart(1, {}, _stageDepth);
        else
            _draw(true);
    };

    /**
     * Main draw function : _drawHeader, _drawBody 로 구성됨.
     * @param forceRedraw
     * @private
     */
    var _draw = function (forceRedraw) {
        if ($.fn.DataTable.isDataTable('#Stage-table')) {
            $('#Stage-table').DataTable().clear().destroy();
        }
        // Always true
        forceRedraw = true;
        if (forceRedraw) {
            _wrapper.empty();
            _wrapper.append(_table = $('<table class="table" id="Stage-table">'));
            if (_styles.tableClass)
                _table.addClass(_styles.tableClass);
            _table.append(_tableHead = $('<thead>'));
            _table.append(_tableBody = $('<tbody>'));
            _drawHeader();
        }
        _drawBody();

        $('#Stage-table').DataTable({
            "ordering": false,
            "searching": false,
            "info": false,
            "paging": false,
            "scrollX": true,
            "scrollY": 400
        });
        $('.dataTables_length').addClass('bs-select');
        scrollToScrollRect();
    };
    /**
     * Table header draw
     * @private
     */
    var _drawHeader = function () {
        var tr = $('<tr>');
        tr.append('<td>Stage 1</td>');
        for (var i = 1; i < _stageDepth; i++) {
            tr.append('<td>Condition</td><td>Stage ' + (i + 1) + '</td>');
        }
        tr.append('<td>Add</td>');
        _tableHead.append(tr);
    };
    /**
     * Table body 의 row 를 생성한다.
     * recursive function.
     * @param context
     * @param stage_data
     * @param depth
     * @param index
     * @param is_last_in_stage
     * @private
     */
    var _buildRows = function (context, stage_data, depth, index, is_last_in_stage) {
        if (context.stageRow == null)
            context.stageRow = new StageRow(context, _rowCallbacks);
        context.stageRow.setStage(depth, stage_data);
        context.stageRow.setRowInfo(depth, index);
        context.stageRow.setIsLastInStage(depth, is_last_in_stage);
        if (stage_data.next) {
            for (var i = 0; i < stage_data.next.length; i++) {
                var is_last = (i === stage_data.next.length - 1);
                _buildRows(context, stage_data.next[i], depth + 1, i, is_last);
            }
        } else {
            context.wrapper.append(context.stageRow.buildRow());
            context.stageRow = null;
        }
    };

    /**
     * Table 의 body 를 draw
     * @private
     */
    var _drawBody = function () {
        _tableBody.empty();
        var currentData = (_mode === 'edit') ? _stageData : _stageDataAdd;
        var context = {'stageRow': null, 'wrapper': _tableBody, 'rowInfo': {}, 'isLastInStage': {}};
        var stage_data, is_last;
        for (var i = 0; i < currentData.length; i++) {
            stage_data = currentData[i];
            is_last = (i === currentData.length - 1);
            _buildRows(context, stage_data, 1, i, is_last);
        }
    };

    var redraw = function () {
        _draw(true);
    };

    /**
     * 외부에서 사용해야하는 function 을 노출한다.
     */
    return {
        init: init,
        setData: setData,
        getData: getData,
        redraw: redraw
    }
})();