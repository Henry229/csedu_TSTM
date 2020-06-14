var ItemHandlers = (function () {
    var _interaction_type, _handler, _subject;
    var _dndMessageInfo = "* Drag and drop to mark your answer.<br>* Click an answer to remove it.";
    function enableUsageInfo(messageInfo) {
        $('.usage-info-button').show();
        $('.usage-info .message').html(messageInfo);
        $('.usage-info-button').on('click', function () {
            $('.usage-info #effect').show();
            setTimeout(function () {
                $( ".usage-info #effect" ).hide( 'slide', {direction: 'up'}, 1000 );
            }, 1500)
        });
        $('.usage-info-button').click();
    }
    var emptyInteractionHandler = function (options) {
        if (this === window) return new emptyInteractionHandler(options);

        this._$container = options.container;

        this.processUI = function (response) {
            /* Empty */
        };
        this.getResponse = function () {
            var identifier = 'RESPONSE';
            var baseType = 'identifier';
            var base = {};
            base[baseType] = 'sample';
            var response = {};
            response[identifier] = {'base': base};
            return response;
        };
    };
    var choiceInteractionHandler = function (options) {
        if (this === window) return new choiceInteractionHandler(options);
        this._$container = options.container;
        this.cardinality = options.data.cardinality;
        this.processUI = function (answer) {
            this.setSavedAnswer(answer);
            $('.label-box').on('click', function () {
                $(this).prev().click();
            });
        };
        this.setSavedAnswer = function (answer) {
            if (typeof answer === 'string')
                answer = [answer];
            var $choice_area = $('.choice-area');
            var choices = $choice_area.find('input');
            for (var i = 0; i < choices.length; i++) {
                var value = $(choices[i]).val();
                if (answer.indexOf(value) !== -1)
                    $(choices[i]).prop('checked', true);
            }
        };
        this.getResponse = function () {
            var $choice_area = $('.choice-area');
            var checked = $choice_area.find('input:checked');
            var results = [];
            for (var i = 0; i < checked.length; i++) {
                results.push($(checked[i]).val());
            }

            var identifier = $choice_area.data('identifier');
            var baseType = $choice_area.data('base-type');
            var base = {};
            var response = {};
            if (this.cardinality === 'multiple') {
                base[baseType] = results;
                response[identifier] = {'list': base};
            } else if (this.cardinality === 'single') {
                base[baseType] = results[0];
                response[identifier] = {'base': base};
            }
            return response
        };
    };
    var orderInteractionHandler = function (options) {
        if (this === window) return new orderInteractionHandler(options);
        this._$container = options.container;

        this.processUI = function (answer) {
            $('.source .qti-choice').addClass('draggable-item');
            $('.source').sortable({
                connectWith: ".result-area"
            }).disableSelection();
            $('.target').sortable({
                connectWith: ".choice-area"
            }).disableSelection();
            $('.source .qti-choice').on('click', function () {
                // Check if $(this) is in target area.
                if ($(this).parent().hasClass('target')) return;

                $('.target').append($(this));
            });
            this.setSavedAnswer(answer);
        };
        this.setSavedAnswer = function (answer) {
            for (var i = 0; i < answer.length; i++) {
                var id = answer[i];
                if (id === "") continue;
                $('.source .qti-choice[data-identifier=' + id + ']').click();
            }
        };

        this.getResponse = function () {
            var $result = $('.result-area li');
            var ordered = [];
            for (var i = 0; i < $result.length; i++) {
                var $el = $result[i];
                ordered.push($($el).data('identifier'));
            }
            var $choice_area = $('.order-interaction-area');
            var identifier = $choice_area.data('identifier');
            var baseType = $choice_area.data('base-type');
            var base = {};
            base[baseType] = ordered;
            var response = {};
            response[identifier] = {'list': base};
            return response;
        };
    };
    var textEntryInteractionHandler = function (options) {
        if (this === window) return new textEntryInteractionHandler(options);
        this._$container = options.container;

        this.processUI = function (answer) {
            this.setSavedAnswer(answer);
        };
        this.setSavedAnswer = function (answer) {
            var $text_entry = $('input.qti-textEntryInteraction');
            $text_entry.val(answer);
        };
        this.getResponse = function () {
            var $text_entry = $('input.qti-textEntryInteraction');
            var result = $text_entry.val();
            //if (result === '')
            //	return null;
            var identifier = $text_entry.data('identifier');
            var baseType = $text_entry.data('base-type');
            var base = {};
            base[baseType] = result;
            var response = {};
            response[identifier] = {'base': base};
            return response;
        };
    };

    var graphicGapMatchInteraction = function (options) {
        if (this === window) return new graphicGapMatchInteraction(options);
        this._$container = options.container;
        var destMap = {};
        var _targets = [];
        var object_variables = options.data.object_variables;
        // Error note review mode 에서는 답을 변경할 수 없다.
        var _review_mode = options.review_mode || false;
        var _answer_restored = false;
        for (var key in object_variables) {
            if (object_variables.hasOwnProperty(key)) {
                this.object_variables = object_variables[key];
                this.interaction_serial = key;
                break;
            }
        }
        var _paper = 'graphic-paper-' + this.interaction_serial;

        this._svg = null;
        this._sources = null;

        this.processUI = function (answer) {
            var self = this;
            var obj = self.object_variables.obj;
            var choices = self.object_variables.choices;
            var svg = SVG(_paper).size(obj.width, obj.height);
            svg.viewbox(0, 0, obj.width, obj.height);
            svg.image(obj.data, obj.width, obj.height);
            self._svg = svg;
            for (var i = 0; i < choices.length; i++) {
                var c = choices[i];
                var shape;
                if (c.shape === 'ellipse') {
                    shape = svg[c.shape](c.rx * 2, c.ry * 2);
                    shape.attr({'cx': c.cx, 'cy': c.cy});
                } else {
                    shape = svg[c.shape](c.width, c.height);
                    shape.attr({'x': c.x, 'y': c.y});
                }

                shape.attr({
                    'fill-opacity': 0.5, 'fill': '#cccccc',
                    'identifier': c.identifier, 'index': i
                });
                destMap[c.identifier] = shape;
                _targets.push(shape);
                var click_cb = function () {
                    // Error note review mode 에서는 답을 변경할 수 없다.
                    if (_answer_restored && _review_mode) return;

                    var index = this.attr('index');
                    var $selected = $('.source .ui-selected');
                    var c = choices[index];
                    if (c['result'] !== undefined && c['result'] !== null) return;
                    c['result'] = $selected.data('identifier');
                    if ($selected.length === 0) return;
                    var href = $selected.find('img').attr('src');
                    var image = self._svg.image(href, this.attr('width'), this.attr('height'));
                    var x, y;
                    if (c.shape === 'ellipse') {
                        x = this.attr('cx') - this.attr('rx');
                        y = this.attr('cy') - this.attr('ry');
                    } else {
                        x = this.attr('x');
                        y = this.attr('y');
                    }
                    image.attr({
                        'x': x, 'y': y, 'preserveAspectRatio': 'none'
                    });
                    image.on('click', function () {
                        if (_review_mode) return;
                        this.remove();
                        c['result'] = null;
                    });
                };
                shape.on('click', click_cb);
            }
            self._sources = $(".source .selectable");
            self._sources.on('click', function (events) {
                $(".source .selectable").removeClass('ui-selected');
                $(this).addClass('ui-selected');
            });
            $('.source .selectable img').draggable({
                appendTo: 'body', helper: "clone", zIndex: 5000,
                start: function (event, ui) {
                    // Error note review mode 에서는 답을 변경할 수 없다.
                    if (_review_mode === false)
                        $(event.target).click();
                },
                stop: function (event, ui) {
                    var m_x = event.pageX, m_y = event.pageY;
                    //console.log("Stop Mouse X: " + event.pageX + " Y: " + event.pageY);
                    for (var i = 0; i < _targets.length; i++) {
                        var t = _targets[i];
                        var bound = t.node.getBoundingClientRect();
                        //console.log("bound rect X: " + bound.x + " Y: " + bound.y);
                        //console.log("bound rect X: " + bound.left + " Y: " + bound.top);
                        //IE returns Returns a ClientRectList with ClientRect objects (which do not contain x and y properties) instead of DOMRect objects
                        var bound_x = bound.x || bound.left;
                        var bound_y = bound.y || bound.top;
                        if (m_x > bound_x && m_x < bound_x + bound.width
                          && m_y > bound_y && m_y < bound_y + bound.height) {
                            t.fire('click');
                        }
                    }
                },
                drag: function (event, ui) {
                }
            });
            this.setSavedAnswer(answer);
            enableUsageInfo(_dndMessageInfo);
        };
        this.setSavedAnswer = function (answer) {
            for (var i = 0; i < answer.length; i++) {
                var ans = answer[i].split(" ");
                if (ans.length < 2) continue;
                $('.source [data-identifier=' + ans[1] + ']').click();
                destMap[ans[0]].fire('click');
            }
            _answer_restored = true;
        };
        this.getResponse = function () {
            var choices = this.object_variables.choices;
            var result = [];
            for (var i = 0; i < choices.length; i++) {
                var c = choices[i];
                if (c.result != null)
                    result.push([c.identifier, c.result]);
            }
            var interaction = $('.qti-graphicGapMatchInteraction');
            var identifier = interaction.data('identifier');
            var baseType = interaction.data('base-type');
            var base = {};
            base[baseType] = result;
            var response = {};
            response[identifier] = {'list': base};
            return response;
        };
    };
    var matchInteraction = function (options) {
        if (this === window) return new matchInteraction(options);
        this._$container = options.container;
        var object_variables = options.data.object_variables;
        for (var key in object_variables) {
            if (object_variables.hasOwnProperty(key)) {
                this.object_variables = object_variables[key];
                this.interaction_serial = key;
                break;
            }
        }

        this.processUI = function (answer) {
            this.setSavedAnswer(answer);
        };
        this.setSavedAnswer = function (answer) {
            var $matchset1 = $('table.matrix thead th');
            var cols = [], i;
            for (i = 1; i < $matchset1.length; i++) {
                cols.push($($matchset1[i]).data('identifier'));
            }
            var rows = {};
            for (i = 0; i < answer.length; i++) {
                var ans = answer[i].split(" ");
                rows[ans[1]] = rows[ans[1]] || [];
                var row = rows[ans[1]];
                row.push(cols.indexOf(ans[0]));
            }
            for (var r in rows) {
                if (rows.hasOwnProperty(r)) {
                    var val = rows[r];
                    var tr = $('.matrix [data-identifier=' + r + ']').parent();
                    var checks = tr.find('td input');
                    for (var j = 0; j < val.length; j++) {
                        $(checks[val[j]]).prop('checked', true);
                    }
                }
            }
        };

        this.getResponse = function () {
            var $matchset1 = $('table.matrix thead th');
            var ids = [], i;
            for (i = 1; i < $matchset1.length; i++) {
                ids.push($($matchset1[i]).data('identifier'));
            }
            var $matchset2 = $('table.matrix tbody tr');
            var result = [];
            for (i = 0; i < $matchset2.length; i++) {
                var id = $($matchset2[i]).find('th').data('identifier');
                var checkboxes = $($matchset2[i]).find('td input');
                for (var k = 0; k < checkboxes.length; k++) {
                    if ($(checkboxes[k]).prop('checked'))
                        result.push([ids[k], id]);
                }
            }

            var interaction = $('.qti-matchInteraction');
            var identifier = interaction.data('identifier');
            var baseType = interaction.data('base-type');
            var base = {};
            base[baseType] = result;
            var response = {};
            response[identifier] = {'list': base};
            return response;
        };
    };
    var associateInteraction = function (options) {
        if (this === window) return new associateInteraction(options);
        this._$container = options.container;

        this.processUI = function (answer) {
            var $choices = $('.choice-area li');
            var choice_num = $choices.length;
            var $result_area = $('.result-area');
            for (var i = 0; i < choice_num / 2; i++) {
                var $li = $('<li class="target-area">');
                var $div_l = $('<div class="target lft" style="height: 33px;">');
                var $div_r = $('<div class="target rgt" style="height: 33px;">');
                $li.append($div_l);
                $li.append($div_r);
                $result_area.append($li);
            }

            $('.source .qti-choice').addClass('draggable-item');
            $('.source').sortable({
                connectWith: ".result-area div"
            }).disableSelection();
            $('.target div').sortable({
                connectWith: ".choice-area"
            }).disableSelection();

            this.setSavedAnswer(answer);
        };

        this.setSavedAnswer = function (answer) {
            var $result_area = $('.result-area .target-area');
            for (var i = 0; i < answer.length; i++) {
                var choices = answer[i].split(' ');
                var left = $('.choice-area li[data-identifier=' + choices[0] + ']');
                var right = $('.choice-area li[data-identifier=' + choices[1] + ']');
                var r = $result_area[i];
                $(r).find('.lft').append(left[0]);
                $(r).find('.rgt').append(right[0]);
            }
        };

        this.getResponse = function () {
            var $result_area = $('.result-area .target-area');
            var results = [];
            for (var i = 0; i < $result_area.length; i++) {
                var r = $result_area[i];
                var left = $(r).find('.lft .qti-choice').data('identifier');
                var right = $(r).find('.rgt .qti-choice').data('identifier');
                left = left || "";
                right = right || "";
                if (left !== "" && right !== "")
                    results.push([left, right]);
            }
            var interaction = $('.qti-associateInteraction');
            var identifier = interaction.data('identifier');
            var baseType = interaction.data('base-type');
            var base = {};
            base[baseType] = results;
            var response = {};
            response[identifier] = {'list': base};
            return response;
        };
    };
    var hotspotInteraction = function (options) {
        if (this === window) return new hotspotInteraction(options);
        this._$container = options.container;
        this.cardinality = options.data.cardinality;
        var object_variables = options.data.object_variables;
        for (var key in object_variables) {
            if (object_variables.hasOwnProperty(key)) {
                this.object_variables = object_variables[key];
                this.interaction_serial = key;
                break;
            }
        }

        this.processUI = function (answer) {
            var self = this;
            var obj = self.object_variables.obj;
            var choices = self.object_variables.choices;
            var svg = SVG('graphic-paper-' + self.interaction_serial).size(obj.width, obj.height);
            svg.viewbox(0, 0, obj.width, obj.height);
            svg.image(obj.data, obj.width, obj.height);
            self._svg = svg;
            for (var i = 0; i < choices.length; i++) {
                var c = choices[i];
                var shape;
                if (c.shape === 'ellipse') {
                    shape = svg[c.shape](c.rx * 2, c.ry * 2);
                    shape.attr({'cx': c.cx, 'cy': c.cy});
                } else {
                    shape = svg[c.shape](c.width, c.height);
                    shape.attr({'x': c.x, 'y': c.y});
                }
                shape.attr({
                    'fill-opacity': 0.5, 'fill': '#cccccc',
                    'identifier': c.identifier, 'index': i
                });
                shape.on('click', function () {
                    var index = this.attr('index');
                    if (self.cardinality === 'single') {
                        for (var i = 0; i < choices.length; i++) {
                            choices[i].shape.attr({'selected': 'false', 'fill': '#cccccc'});
                        }
                    }
                    var c = choices[index];
                    if (c.shape.attr('selected') === 'true') {
                        c.shape.attr({'selected': 'false', 'fill': '#cccccc'});
                    } else {
                        c.shape.attr({'selected': 'true', 'fill': '#1782dd'});
                    }

                });
                c.shape = shape;
            }
            this.setSavedAnswer(answer);
            // enableUsageInfo(_dndMessageInfo);
        };

        this.setSavedAnswer = function (answer) {
            if (typeof answer === 'string')
                answer = [answer];
            var choices = this.object_variables.choices;
            for (var i = 0; i < choices.length; i++) {
                var c = choices[i];
                if (answer.indexOf(c.shape.attr('identifier')) !== -1) {
                    c.shape.fire('click');
                }
            }
        };

        this.getResponse = function () {
            var results = [];
            var choices = this.object_variables.choices;
            for (var i = 0; i < choices.length; i++) {
                var c = choices[i];
                if (c.shape.attr('selected') === 'true') {
                    results.push(c.shape.attr('identifier'));
                }
            }

            var interaction = $('.qti-hotspotInteraction');
            var identifier = interaction.data('identifier');
            var baseType = interaction.data('base-type');
            var base = {};
            var response = {};
            if (this.cardinality === 'multiple') {
                base[baseType] = results;
                response[identifier] = {'list': base};
            } else if (this.cardinality === 'single') {
                base[baseType] = results[0];
                response[identifier] = {'base': base};
            }
            return response;
        };
    };
    var inlineChoiceInteraction = function (options) {
        if (this === window) return new inlineChoiceInteraction(options);
        this._$container = options.container;
        this.cardinality = options.data.cardinality;
        this.processUI = function (answer) {
            this.setSavedAnswer(answer);
        };
        this.setSavedAnswer = function (answer) {
            if (typeof answer === 'string')
                answer = [answer];
            var interactions = $('.qti-interaction');
            for (var i = 0; i < interactions.length; i++) {
                var $interaction = $(interactions[i]);
                var id_key = $interaction.data('identifier');
                if (Array.isArray(answer)) {
                    $interaction.val(answer[i]);
                }
                else {
                    var val = answer[id_key] || '';
                    $interaction.val(val);
                }
            }
        };

        this.getResponse = function () {
            var interactions = $('.qti-interaction');
            var response = {};
            var results = [];
            var base = {};
            for (var i = 0; i < interactions.length; i++) {
                base = {};
                var $interaction = $(interactions[i]);
                var identifier = $interaction.data('identifier');
                var baseType = $interaction.data('base-type');
                results.push($interaction.val());
                base[baseType] = $interaction.val();
                response[identifier] = {'base': base};
            }
            if (this.cardinality === 'multiple') {
                base[baseType] = results;
                response[identifier] = {'list': base};
            } else if (this.cardinality === 'single') {
                // base[baseType] = results[0];
                // response[identifier] = {'base': base};
            }
            return response;
        };
    };
    var extendedTextInteraction = function (options) {
        if (this === window) return new extendedTextInteraction(options);
        this._$container = options.container;
        this.cardinality = options.data.cardinality;
        this.writing_text = null;
        this.formData = null;
        this.fileNames = null;

        /**
         * To handle writing item with file uploading.
         */
        this.readFile = function(file) {
            var self = this;
            var interactions = $('.qti-uploadInteraction');
            interactions.find('.file-names ul').empty();
            self.formData = null;
            if (file && file.files.length > 0) {
                //This fileName and fileType are just for response checker in PHP.
                self.fileName = file.files[0].name;
                self.fileType = file.files[0].type;
                self.formData = new FormData();
                self.fileNames = [];
                for (var i=0; i<file.files.length; i++) {
                    self.formData.append('files', file.files[i]);
                    self.fileNames.push(file.files[i].name);
                    var li = $('<li>').html(file.files[i].name);
                    interactions.find('.file-names ul').append(li);
                }
            }
        };

        this.processUI = function (answer) {
            var self = this;
            if (_subject.toLowerCase() === 'writing') {
                $('.qti-uploadInteraction input[type=file]').on("change", function () {
                    self.readFile(this);
                });
            }
            this.setSavedAnswer(answer);
        };
        this.setSavedAnswer = function (answer) {
            var answers = [];
            if (typeof answer === 'string')
                answers.push(answer);
            else if (answer.writing_text)
                answers.push(answer.writing_text);
            else
                answers = answer;
            var interactions = $('.qti-extendedTextInteraction');
            for (var i = 0; i < interactions.length; i++) {
                var $interaction = $(interactions[i]);
                $interaction.find('textarea').val(answers[i]);
            }
            if (answer.file_names) {
                this.fileNames = [];
                interactions = $('.qti-uploadInteraction');
                for (i = 0; i < answer.file_names.length; i++) {
                    var li = $('<li>').html(answer.file_names[i]);
                    interactions.find('.file-names ul').append(li);
                    this.fileNames.push(answer.file_names[i]);
                }
            }
        };
        this.getResponse = function () {
            var interactions = $('.qti-extendedTextInteraction');
            var response = {};
            var results = [];
            for (var i = 0; i < interactions.length; i++) {
                var base = {};
                var $interaction = $(interactions[i]);
                var identifier = $interaction.data('identifier');
                var baseType = $interaction.data('base-type');
                results.push($interaction.find('textarea').val());
                response[identifier] = {'base': base};
                // Set writing_text to save as a file in the server.
                // Only single text file is accepted now.
                this.writing_text = $interaction.find('textarea').val();
            }
            if (this.cardinality === 'multiple') {
                base[baseType] = results;
                response[identifier] = {'list': base};
            } else if (this.cardinality === 'single') {
                base[baseType] = results[0];
                response[identifier] = {'base': base};
            }

            if (this.writing_text !== null && this.writing_text !== '')
                response['writing_text'] = this.writing_text;
            if (_subject.toLowerCase() === 'writing') {
                response['formData'] = this.formData;
                response['fileNames'] = this.fileNames;
            }
            return response;
        };
    };
    var uploadInteraction = function (options) {
        if (this === window) return new uploadInteraction(options);
        this._$container = options.container;
        this.cardinality = options.data.cardinality;
        this.fileData = "";
        this.fileName = "";
        this.fileType = "";
        this.writing_text = null;
        this.formData = null;
        this.fileNames = null;

        this.readFile = function(file) {
            var self = this;
            var interactions = $('.qti-uploadInteraction');
            interactions.find('.file-names ul').empty();
            self.formData = null;
            if (file && file.files.length > 0) {
                //This fileName and fileType are just for response checker in PHP.
                self.fileName = file.files[0].name;
                self.fileType = file.files[0].type;
                self.formData = new FormData();
                self.fileNames = [];
                for (var i=0; i<file.files.length; i++) {
                    self.formData.append('files', file.files[i]);
                    self.fileNames.push(file.files[i].name);
                    var li = $('<li>').html(file.files[i].name);
                    interactions.find('.file-names ul').append(li);
                }
            }
        };

        this.processUI = function (answer) {
            var self = this;
            $('.qti-uploadInteraction input[type=file]').on("change", function () {
                self.readFile(this);
            });
            this.setSavedAnswer(answer);
        };

        this.setSavedAnswer = function (answer) {
            if (typeof answer === 'string')
                answer = [answer];
            var interactions, $interaction, i;
            if (answer.writing_text) {
                interactions = $('.qti-extendedTextInteraction');
                for (i = 0; i < interactions.length; i++) {
                    $interaction = $(interactions[i]);
                    $interaction.find('textarea').val(answer.writing_text);
                }
            }
            if (answer.file_names) {
                this.fileNames = [];
                interactions = $('.qti-uploadInteraction');
                for (i = 0; i < answer.file_names.length; i++) {
                    var li = $('<li>').html(answer.file_names[i]);
                    interactions.find('.file-names ul').append(li);
                    this.fileNames.push(answer.file_names[i]);
                }
            }
        };

        this.getResponse = function () {
            var $interaction = $('.qti-uploadInteraction');
            var response = {};
            var base = {};
            var identifier = $interaction.data('identifier');
            var baseType = $interaction.data('base-type');
            //var $file = $('.file-upload input');
            base[baseType] = {
                //"data": this.fileData,
                "data": "",
                "mime": this.fileType,
                "name": this.fileName
            };
            response[identifier] = {'base': base};
            response['formData'] = this.formData;
            response['fileNames'] = this.fileNames;
            if (_subject.toLowerCase() === 'writing') {
                var writing_interaction = $('.qti-extendedTextInteraction');
                for (var i = 0; i < writing_interaction.length; i++) {
                    this.writing_text = writing_interaction.find('textarea').val();
                }
                if (this.writing_text !== null && this.writing_text !== '')
                response['writing_text'] = this.writing_text;
            }
            return response;
        };
    };
    var hottextInteraction = function (options) {
        if (this === window) return new hottextInteraction(options);
        this._$container = options.container;
        this.cardinality = options.data.cardinality;
        this.interaction = options.data.interactions[0];
        var attributes = this.interaction.attributes || {};
        if (this.cardinality === 'multiple' && attributes.maxChoices === 0) {
            this.maxChoices = 0;
        } else {
            this.maxChoices = attributes.maxChoices || 1;
        }
        if (this.cardinality === 'multiple' && attributes.maxChoices === 0) {
            this.minChoices = 0;
        } else {
            this.minChoices = attributes.minChoices || 1;
        }


        this.processUI = function (answer) {
            var self = this;
            this.setSavedAnswer(answer);
            $('.qti-interaction .qti-choice input').on('click', function () {
                var checked = $('.qti-interaction .qti-choice input:checked');
                if (self.cardinality !== 'single' && self.maxChoices !== 0 && checked.length > self.maxChoices) {
                    $(this).prop('checked', false);
                }
            });
        };
        this.setSavedAnswer = function (answer) {
            if (typeof answer === 'string')
                answer = [answer];
            var interactions = $('.qti-interaction');
            for (var i = 0; i < interactions.length; i++) {
                var $interaction = $(interactions[i]);
                var choices = $interaction.find('.qti-choice');
                for (var k = 0; k < choices.length; k++) {
                    if (answer.indexOf($(choices[k]).data('identifier')) !== -1)
                        $(choices[k]).find('input').prop('checked', true);
                }
            }
        };
        this.getResponse = function () {
            var interactions = $('.qti-interaction');
            var response = {};
            for (var i = 0; i < interactions.length; i++) {
                var base = {};
                var results = [];
                var $interaction = $(interactions[i]);
                var identifier = $interaction.data('identifier');
                var baseType = $interaction.data('base-type');
                var choices = $interaction.find('.qti-choice');
                for (var k = 0; k < choices.length; k++) {
                    if ($(choices[k]).find('input').prop('checked')) {
                        results.push($(choices[k]).data('identifier'));
                    }
                }
                if (this.cardinality === 'multiple') {
                    base[baseType] = results;
                    response[identifier] = {'list': base};
                } else if (this.cardinality === 'single') {
                    base[baseType] = results[0];
                    response[identifier] = {'base': base};
                }
            }
            return response;
        };
    };
    var mediaInteraction = function (options) {
        if (this === window) return new mediaInteraction(options);
        this._$container = options.container;
        this.cardinality = options.data.cardinality;
        var object_variables = options.data.object_variables;
        for (var key in object_variables) {
            if (object_variables.hasOwnProperty(key)) {
                this.object_variables = object_variables[key];
                this.interaction_serial = key;
                break;
            }
        }

        this.processUI = function (answer) {
            var obj = this.object_variables.obj;
            var $media_container = $('.media-container');
            var $audio = $('<audio controls>');
            $audio.width(obj.width);
            $audio.height(obj.height);
            var $source = $('<source>');
            $source.attr('src', obj.data);
            $source.attr('type', obj.type);
            $audio.append($source);
            $media_container.append($audio);
            this.setSavedAnswer(answer);
        };
        this.setSavedAnswer = function (answer) {
            if (typeof answer === 'string')
                answer = [answer];
            var interactions = $('.qti-interaction');
            for (var i = 0; i < interactions.length; i++) {
                var $interaction = $(interactions[i]);
                $interaction.val(answer[i]);
            }
        };

        this.getResponse = function () {
            var interactions = $('.qti-interaction');
            var response = {};
            var results = [];
            var identifier = '';
            var baseType = '';
            for (var i = 0; i < interactions.length; i++) {
                var base = {};
                var $interaction = $(interactions[i]);
                var id_temp = $interaction.data('identifier');
                var base_temp = $interaction.data('base-type');
                if (id_temp !== undefined && base_temp !== undefined) {
                    identifier = id_temp;
                    baseType = base_temp;
                }
                results.push($interaction.val());
                response[identifier] = {'base': base};
            }
            if (this.cardinality === 'multiple') {
                base[baseType] = results;
                response[identifier] = {'list': base};
            } else if (this.cardinality === 'single') {
                base[baseType] = results[0];
                response[identifier] = {'base': base};
            }
            return response;
        };
    };
    var gapMatchInteraction = function (options) {
        if (this === window) return new gapMatchInteraction(options);
        this._$container = options.container;
        this.cardinality = options.data.cardinality;

        this.processUI = function (answer) {
            $('.source .qti-choice').draggable({
                scope: "tasks",
                zIndex: 10,
                opacity: 0.95,
                helper: "clone"
            });
            $('.qti-gap').droppable({
                scope: "tasks",
                drop: function (event, ui) {
                    var target = event.target;
                    target.source = ui.draggable;
                    $(target).find('.gapmatch-content').html(ui.draggable.find('.qti-block').html());
                }
            });
            this.setSavedAnswer(answer);
        };

        this.setSavedAnswer = function (answer) {
            if (typeof answer === 'string')
                answer = [answer];
            for (var i = 0; i < answer.length; i++) {
                var ans = answer[i].split(" ");
                var $source = $('.source [data-identifier=' + ans[0] + ']');
                var $target = $('.qti-gap[data-identifier=' + ans[1] + ']');
                $target[0].source = $source;
                $target.find('.gapmatch-content').html($source.find('.qti-block').html());
            }
        };

        this.getResponse = function () {
            var $interaction = $('.qti-interaction');
            var response = {};
            var base = {};
            var results = [];
            var $gaps = $('.qti-gap');
            for (var k = 0; k < $gaps.length; k++) {
                var gap = $gaps[k];
                var source = gap.source;
                if (source === undefined) continue;
                results.push([$(source).data('identifier'), $(gap).data('identifier')]);
            }
            var identifier = $interaction.data('identifier');
            var baseType = $interaction.data('base-type');
            if (this.cardinality === 'multiple') {
                base[baseType] = results;
                response[identifier] = {'list': base};
            } else if (this.cardinality === 'single') {
                base[baseType] = results[0];
                response[identifier] = {'base': base};
            }
            return response;
        };
    };


    var handlers = {
        'choiceInteraction': choiceInteractionHandler,
        'orderInteraction': orderInteractionHandler,
        'textEntryInteraction': textEntryInteractionHandler,
        'graphicGapMatchInteraction': graphicGapMatchInteraction,
        'matchInteraction': matchInteraction,
        'associateInteraction': associateInteraction,
        'hotspotInteraction': hotspotInteraction,
        'inlineChoiceInteraction': inlineChoiceInteraction,
        'extendedTextInteraction': extendedTextInteraction,
        'hottextInteraction': hottextInteraction,
        'mediaInteraction': mediaInteraction,
        'gapMatchInteraction': gapMatchInteraction,
        'uploadInteraction': uploadInteraction
    };
    var getInteractionHandler = function (interaction_type) {
        console.log(interaction_type);
        var h = handlers[interaction_type];
        if (h === undefined)
            h = emptyInteractionHandler;
        return h;
    };

    var init = function (interaction_type, options) {
        _interaction_type = interaction_type;
        _subject = options.data.subject;
        var h = getInteractionHandler(interaction_type);
        _handler = h(options);
        return _handler;
    };

    return {
        init: init
    }
})();