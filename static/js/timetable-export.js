(function () {
    var COLORS = {
        "必修": { fill: "#e7efff", text: "#1e3a8a", bar: "#1d4ed8" },
        "選修": { fill: "#e7f6f1", text: "#115e59", bar: "#0f766e" },
        "通識": { fill: "#fff4e5", text: "#92400e", bar: "#b45309" }
    };

    function payload() {
        var node = document.getElementById("timetable-export-data");
        if (!node) return null;
        try {
            return JSON.parse(node.textContent);
        } catch (error) {
            return null;
        }
    }

    function escapeHtml(value) {
        return String(value == null ? "" : value).replace(/[&<>"']/g, function (ch) {
            return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch];
        });
    }

    function rowsOf(data) {
        var rows = [];
        data.periods.forEach(function (item) {
            if (item.period === 5) rows.push({ kind: "break" });
            rows.push({ kind: "period", period: item.period, time: item.time || "" });
        });
        return rows;
    }

    function rowIndex(period) {
        return period < 5 ? period - 1 : period;
    }

    function segments(course) {
        if (course.start_period <= 4 && course.end_period >= 5) {
            return [[course.start_period, 4], [5, course.end_period]];
        }
        return [[course.start_period, course.end_period]];
    }

    function fileStamp() {
        var now = new Date();
        var pad = function (n) { return String(n).padStart(2, "0"); };
        return now.getFullYear() + pad(now.getMonth() + 1) + pad(now.getDate());
    }

    function courseLines(course) {
        return [
            course.name,
            course.teacher || "",
            course.start_period + "–" + course.end_period + "節 · " + course.credits + "學分",
            course.target_class ? "班級 " + course.target_class : ""
        ].filter(Boolean);
    }

    function exportPdf(data) {
        var rows = rowsOf(data);
        var occupied = {};
        var blocks = [];
        data.courses.forEach(function (course) {
            segments(course).forEach(function (range) {
                var start = rowIndex(range[0]);
                var span = rowIndex(range[1]) - start + 1;
                var day = course.weekday - 1;
                blocks.push({ course: course, row: start, day: day, span: span });
                for (var i = 0; i < span; i += 1) occupied[(start + i) + ":" + day] = true;
            });
        });

        var body = rows.map(function (row, index) {
            if (row.kind === "break") {
                return '<tr class="break"><td colspan="8">午休</td></tr>';
            }
            var cells = '<th><span>' + row.period + '</span>' +
                (row.time ? '<small>' + escapeHtml(row.time) + '</small>' : '') + '</th>';
            for (var day = 0; day < 7; day += 1) {
                var block = blocks.find(function (item) {
                    return item.row === index && item.day === day;
                });
                if (block) {
                    var course = block.course;
                    var color = COLORS[course.course_type] || COLORS["選修"];
                    cells += '<td class="slot" rowspan="' + block.span + '">' +
                        '<div class="block" style="background:' + color.fill + ';color:' + color.text + ';border-left-color:' + color.bar + '">' +
                        courseLines(course).map(function (line, lineIndex) {
                            return '<p class="' + (lineIndex === 0 ? "name" : "meta") + '">' + escapeHtml(line) + '</p>';
                        }).join("") +
                        '</div></td>';
                } else if (!occupied[index + ":" + day]) {
                    cells += '<td class="slot"></td>';
                }
            }
            return '<tr>' + cells + '</tr>';
        }).join("");

        var html = '<!DOCTYPE html><html lang="zh-Hant"><head><meta charset="utf-8"><title>課表 ' +
            escapeHtml(data.display_name) + '</title><style>' +
            '@page{size:A4 landscape;margin:12mm}*{box-sizing:border-box}body{margin:0;color:#111827;font-family:"Microsoft JhengHei","PingFang TC",sans-serif}' +
            'h1{margin:0;font-size:22px}header p{margin:4px 0 0;color:#4b5563;font-size:13px}' +
            'table{width:100%;margin-top:14px;border-collapse:collapse;table-layout:fixed}' +
            'th,td{border:1px solid #e5e7eb;padding:4px;vertical-align:top;font-weight:500}' +
            'thead th{background:#f9fafb;text-align:center;font-size:13px;height:28px}' +
            'tbody th{width:78px;background:#f9fafb;text-align:center;font-size:12px}' +
            'tbody th span{display:block}tbody th small{display:block;color:#6b7280;font-size:10px}' +
            'td.slot{height:42px}.block{min-height:100%;padding:4px 6px;border-left:3px solid;border-radius:6px}' +
            '.name{margin:0;font-size:12px;font-weight:700;line-height:1.35}.meta{margin:1px 0 0;font-size:10px;line-height:1.35}' +
            '.break td{text-align:center;letter-spacing:.2em;color:#6b7280;background:#f9fafb;font-size:11px;height:18px}' +
            '.hint{margin-top:10px;color:#6b7280;font-size:12px}.no-print{margin-top:12px}' +
            '@media print{.no-print{display:none}}' +
            '</style></head><body><header><h1>個人課表</h1><p>' +
            escapeHtml(data.display_name) + '（' + escapeHtml(data.username) + '） · ' +
            escapeHtml(data.semester) + '</p></header><table><thead><tr><th>節次</th>' +
            data.weekdays.map(function (name) { return '<th>' + escapeHtml(name) + '</th>'; }).join('') +
            '</tr></thead><tbody>' + body + '</tbody></table>' +
            '<p class="hint">開課班級會一併列出。系統目前沒有獨立的教室欄位。</p>' +
            '<p class="no-print">請在列印對話框選擇「儲存為 PDF」。</p>' +
            '<script>window.addEventListener("load",function(){window.print();});<\/script></body></html>';

        var win = window.open("", "_blank");
        if (!win) {
            window.alert("瀏覽器擋住了匯出視窗，請允許彈出視窗後再試一次。");
            return;
        }
        win.document.open();
        win.document.write(html);
        win.document.close();
    }

    function wrapText(ctx, text, maxWidth) {
        var lines = [];
        var line = "";
        Array.from(text).forEach(function (ch) {
            var next = line + ch;
            if (line && ctx.measureText(next).width > maxWidth) {
                lines.push(line);
                line = ch;
            } else {
                line = next;
            }
        });
        if (line) lines.push(line);
        return lines;
    }

    function exportPng(data) {
        var scale = 2;
        var periodWidth = 132;
        var dayWidth = 168;
        var rowHeight = 72;
        var pad = 36;
        var headerHeight = 96;
        var rows = rowsOf(data);
        var width = pad * 2 + periodWidth + dayWidth * 7;
        var height = pad * 2 + headerHeight + rows.length * rowHeight + 28;
        var canvas = document.createElement("canvas");
        canvas.width = width * scale;
        canvas.height = height * scale;
        var ctx = canvas.getContext("2d");
        ctx.scale(scale, scale);
        ctx.fillStyle = "#ffffff";
        ctx.fillRect(0, 0, width, height);
        ctx.fillStyle = "#111827";
        ctx.font = "700 28px 'Microsoft JhengHei', sans-serif";
        ctx.fillText("個人課表", pad, pad + 32);
        ctx.font = "16px 'Microsoft JhengHei', sans-serif";
        ctx.fillStyle = "#4b5563";
        ctx.fillText(data.display_name + "（" + data.username + "） · " + data.semester, pad, pad + 60);

        var originX = pad;
        var originY = pad + headerHeight;
        ctx.strokeStyle = "#e5e7eb";
        ctx.lineWidth = 1;
        ctx.font = "700 14px 'Microsoft JhengHei', sans-serif";
        ctx.fillStyle = "#111827";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText("節次", originX + periodWidth / 2, originY + 22);
        data.weekdays.forEach(function (name, index) {
            ctx.fillText(name, originX + periodWidth + dayWidth * index + dayWidth / 2, originY + 22);
        });

        var tableTop = originY + 40;
        rows.forEach(function (row, index) {
            var y = tableTop + index * rowHeight;
            ctx.fillStyle = row.kind === "break" ? "#f9fafb" : "#ffffff";
            ctx.fillRect(originX, y, periodWidth + dayWidth * 7, rowHeight);
            ctx.strokeRect(originX, y, periodWidth, rowHeight);
            for (var day = 0; day < 7; day += 1) {
                ctx.strokeRect(originX + periodWidth + day * dayWidth, y, dayWidth, rowHeight);
            }
            ctx.fillStyle = "#111827";
            ctx.font = "700 13px 'Microsoft JhengHei', sans-serif";
            if (row.kind === "break") {
                ctx.fillStyle = "#6b7280";
                ctx.fillText("午休", originX + (periodWidth + dayWidth * 7) / 2, y + rowHeight / 2);
            } else {
                ctx.fillText("第" + row.period + "節", originX + periodWidth / 2, y + (row.time ? 24 : rowHeight / 2));
                if (row.time) {
                    ctx.font = "12px 'Microsoft JhengHei', sans-serif";
                    ctx.fillStyle = "#6b7280";
                    ctx.fillText(row.time, originX + periodWidth / 2, y + 46);
                }
            }
        });

        data.courses.forEach(function (course) {
            var color = COLORS[course.course_type] || COLORS["選修"];
            segments(course).forEach(function (range) {
                var start = rowIndex(range[0]);
                var span = rowIndex(range[1]) - start + 1;
                var x = originX + periodWidth + (course.weekday - 1) * dayWidth + 6;
                var y = tableTop + start * rowHeight + 6;
                var boxWidth = dayWidth - 12;
                var boxHeight = span * rowHeight - 12;
                ctx.fillStyle = color.fill;
                ctx.fillRect(x, y, boxWidth, boxHeight);
                ctx.fillStyle = color.bar;
                ctx.fillRect(x, y, 4, boxHeight);
                ctx.fillStyle = color.text;
                ctx.textAlign = "left";
                ctx.textBaseline = "top";
                var cursor = y + 8;
                courseLines(course).forEach(function (line, lineIndex) {
                    ctx.font = (lineIndex === 0 ? "700 14px " : "12px ") + "'Microsoft JhengHei', sans-serif";
                    wrapText(ctx, line, boxWidth - 18).forEach(function (part) {
                        if (cursor <= y + boxHeight - 16) ctx.fillText(part, x + 10, cursor);
                        cursor += lineIndex === 0 ? 18 : 16;
                    });
                });
            });
        });

        ctx.textAlign = "left";
        ctx.fillStyle = "#6b7280";
        ctx.font = "13px 'Microsoft JhengHei', sans-serif";
        ctx.fillText("開課班級會一併列出。系統目前沒有獨立的教室欄位。", pad, height - 28);

        var link = document.createElement("a");
        link.href = canvas.toDataURL("image/png");
        link.download = "課表-" + data.username + "-" + fileStamp() + ".png";
        link.click();
    }

    document.addEventListener("DOMContentLoaded", function () {
        var menu = document.getElementById("export-menu");
        var toggle = document.getElementById("export-toggle");
        var panel = document.getElementById("export-panel");
        if (!menu || !toggle || !panel) return;

        function closeMenu() {
            panel.hidden = true;
            toggle.setAttribute("aria-expanded", "false");
        }

        toggle.addEventListener("click", function (event) {
            event.stopPropagation();
            var open = panel.hidden;
            panel.hidden = !open;
            toggle.setAttribute("aria-expanded", open ? "true" : "false");
        });
        document.addEventListener("click", function (event) {
            if (!menu.contains(event.target)) closeMenu();
        });
        document.addEventListener("keydown", function (event) {
            if (event.key === "Escape") closeMenu();
        });
        panel.addEventListener("click", function (event) {
            var button = event.target.closest("[data-export]");
            if (!button) return;
            var data = payload();
            closeMenu();
            if (!data) return;
            if (button.getAttribute("data-export") === "pdf") exportPdf(data);
            if (button.getAttribute("data-export") === "png") exportPng(data);
        });
    });
})();
