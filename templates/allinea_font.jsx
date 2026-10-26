// Allinea le grandezze dei testi di cover.psd e slide.psd a quelle di end.psd.
// Mettilo nella stessa cartella dei tre PSD, poi in Photoshop:
// File > Script > Sfoglia... (File > Scripts > Browse...) e scegli questo file.
// Per ogni livello di testo con lo stesso nome (TITLE, BODY, LABEL, HANDLE, ...)
// copia da end.psd dimensione del font e interlinea. Il resto non viene toccato.

#target photoshop
app.bringToFront();

var FOLDER = File($.fileName).parent;
var REF = "end.psd";
var TARGETS = ["cover.psd", "slide.psd"];

var oldType = app.preferences.typeUnits;
app.preferences.typeUnits = TypeUnits.PIXELS;

function slotName(name) {
    return name.replace(/[{}]/g, "").replace(/^\s+|\s+$/g, "").toUpperCase();
}

function textLayers(container, out) {
    for (var i = 0; i < container.layers.length; i++) {
        var layer = container.layers[i];
        if (layer.typename === "LayerSet") {
            textLayers(layer, out);
        } else if (layer.kind === LayerKind.TEXT) {
            out.push(layer);
        }
    }
    return out;
}

function openFile(name) {
    var f = new File(FOLDER + "/" + name);
    if (!f.exists) return null;
    return app.open(f);
}

var refDoc = openFile(REF);
if (!refDoc) {
    alert("Non trovo " + REF + " nella cartella dello script:\n" + FOLDER.fsName);
} else {
    // grandezze di riferimento da end.psd
    var ref = {};
    var refLayers = textLayers(refDoc, []);
    for (var i = 0; i < refLayers.length; i++) {
        var t = refLayers[i].textItem;
        ref[slotName(refLayers[i].name)] = {
            size: t.size.as("px"),
            auto: t.useAutoLeading,
            leading: t.useAutoLeading ? null : t.leading.as("px")
        };
    }
    refDoc.close(SaveOptions.DONOTSAVECHANGES);

    var report = [];
    for (var j = 0; j < TARGETS.length; j++) {
        var doc = openFile(TARGETS[j]);
        if (!doc) {
            report.push(TARGETS[j] + ": non trovato");
            continue;
        }
        var changed = [];
        var layers = textLayers(doc, []);
        for (var k = 0; k < layers.length; k++) {
            var key = slotName(layers[k].name);
            var r = ref[key];
            if (!r) continue;
            var item = layers[k].textItem;
            item.size = r.size;
            if (r.auto) {
                item.useAutoLeading = true;
            } else {
                item.useAutoLeading = false;
                item.leading = r.leading;
            }
            changed.push(key + " " + Math.round(r.size) + "px");
        }
        doc.save();
        doc.close(SaveOptions.DONOTSAVECHANGES);
        report.push(TARGETS[j] + ": " + (changed.length ? changed.join(", ") : "nessun livello in comune"));
    }
    alert("Grandezze allineate a " + REF + ":\n\n" + report.join("\n") +
          "\n\nSe un testo ora esce dalla sua casella, allarga la casella in Photoshop.");
}

app.preferences.typeUnits = oldType;
