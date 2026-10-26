// Crea i template dei post di @you.didnot.know: cover.psd, slide.psd, end.psd.
// In Photoshop: File > Script > Sfoglia... (File > Scripts > Browse...) e scegli questo file.
// I PSD vengono salvati nella stessa cartella dello script. Poi modificali come vuoi:
// basta non rinominare i livelli IMAGE, TITLE, BODY, HIGHLIGHT, LABEL, NUMBER, HANDLE, CREDIT.

#target photoshop
app.bringToFront();

var W = 1080, H = 1350;
var FOLDER = File($.fileName).parent;
var C = {
    bg: "0B0C10",      // fondo quasi nero
    text: "F4F0E8",    // bianco caldo
    muted: "DAD5CB",   // testo secondario
    accent: "E6B65C",  // ambra
    placeholder: "3A3F52"
};
// Font (nomi PostScript). Se non sono installati, Photoshop ne usa uno sostitutivo:
// installa i file .ttf della cartella "fonts" prima di lanciare lo script.
var F = {
    serif: "InstrumentSerif-Regular",
    serifItalic: "InstrumentSerif-Italic",
    sans: "Archivo-Regular",
    mono: "SpaceMono-Regular"
};

var oldUnits = app.preferences.rulerUnits, oldType = app.preferences.typeUnits;
app.preferences.rulerUnits = Units.PIXELS;
app.preferences.typeUnits = TypeUnits.PIXELS;

function rgb(hex) {
    var c = new SolidColor();
    c.rgb.hexValue = hex;
    return c;
}

function newDoc(name) {
    var doc = app.documents.add(W, H, 72, name, NewDocumentMode.RGB, DocumentFill.TRANSPARENT);
    var bg = doc.artLayers.add();
    bg.name = "Sfondo";
    doc.selection.selectAll();
    doc.selection.fill(rgb(C.bg));
    doc.selection.deselect();
    return doc;
}

function rect(doc, name, x0, y0, x1, y1, hex, opacity) {
    var layer = doc.artLayers.add();
    layer.name = name;
    doc.selection.select([[x0, y0], [x1, y0], [x1, y1], [x0, y1]]);
    doc.selection.fill(rgb(hex));
    doc.selection.deselect();
    if (opacity !== undefined) layer.opacity = opacity;
    return layer;
}

// Sfumatura dal trasparente al fondo (per leggere il testo sopra la foto).
// Se il livello di riempimento sfumato non riesce, ripiega su bande semitrasparenti.
function scrim(doc, name, y0, y1) {
    try {
        doc.selection.select([[0, y0], [W, y0], [W, y1], [0, y1]]);
        var d = new ActionDescriptor(), ref = new ActionReference();
        ref.putClass(stringIDToTypeID("contentLayer"));
        d.putReference(charIDToTypeID("null"), ref);
        var layerDesc = new ActionDescriptor();
        var grad = new ActionDescriptor();
        grad.putUnitDouble(charIDToTypeID("Angl"), charIDToTypeID("#Ang"), -90);
        grad.putEnumerated(charIDToTypeID("Type"), charIDToTypeID("GrdT"), charIDToTypeID("Lnr "));
        var g = new ActionDescriptor();
        g.putString(charIDToTypeID("Nm  "), "Scrim");
        g.putEnumerated(charIDToTypeID("GrdF"), charIDToTypeID("GrdF"), charIDToTypeID("CstS"));
        g.putDouble(charIDToTypeID("Intr"), 4096);
        var colors = new ActionList();
        for (var i = 0; i < 2; i++) {
            var stop = new ActionDescriptor(), col = new ActionDescriptor();
            col.putDouble(charIDToTypeID("Rd  "), 11);
            col.putDouble(charIDToTypeID("Grn "), 12);
            col.putDouble(charIDToTypeID("Bl  "), 16);
            stop.putObject(charIDToTypeID("Clr "), charIDToTypeID("RGBC"), col);
            stop.putEnumerated(charIDToTypeID("Type"), charIDToTypeID("Clry"), charIDToTypeID("UsrS"));
            stop.putInteger(charIDToTypeID("Lctn"), i * 4096);
            stop.putInteger(charIDToTypeID("Mdpn"), 50);
            colors.putObject(charIDToTypeID("Clrt"), stop);
        }
        g.putList(charIDToTypeID("Clrs"), colors);
        var transp = new ActionList();
        var ops = [[0, 0], [4096, 100]];
        for (var j = 0; j < ops.length; j++) {
            var t = new ActionDescriptor();
            t.putUnitDouble(charIDToTypeID("Opct"), charIDToTypeID("#Prc"), ops[j][1]);
            t.putInteger(charIDToTypeID("Lctn"), ops[j][0]);
            t.putInteger(charIDToTypeID("Mdpn"), 50);
            transp.putObject(charIDToTypeID("TrnS"), t);
        }
        g.putList(charIDToTypeID("Trns"), transp);
        grad.putObject(charIDToTypeID("Grad"), charIDToTypeID("Grdn"), g);
        layerDesc.putObject(charIDToTypeID("Type"), stringIDToTypeID("gradientLayer"), grad);
        d.putObject(charIDToTypeID("Usng"), stringIDToTypeID("contentLayer"), layerDesc);
        executeAction(charIDToTypeID("Mk  "), d, DialogModes.NO);
        doc.activeLayer.name = name;
        doc.selection.deselect();
    } catch (e) {
        doc.selection.deselect();
        var steps = 8, h = (y1 - y0) / steps;
        for (var k = 0; k < steps; k++) {
            rect(doc, name + " " + (k + 1), 0, y0 + k * h, W, y0 + (k + 1) * h, C.bg, Math.round((k + 1) * 100 / steps));
        }
    }
}

// Casella di testo (testo paragrafo) con un esempio: il sistema ne copia lo stile.
function text(doc, name, sample, x, y, w, h, font, size, hex, opts) {
    opts = opts || {};
    var layer = doc.artLayers.add();
    layer.kind = LayerKind.TEXT;
    var t = layer.textItem;
    t.kind = TextType.PARAGRAPHTEXT;
    t.contents = sample;
    t.font = font;
    t.size = size;
    t.color = rgb(hex);
    t.position = [x, y];
    t.width = w;
    t.height = h;
    t.justification = opts.align || Justification.LEFT;
    if (opts.leading) {
        t.useAutoLeading = false;
        t.leading = opts.leading;
    }
    if (opts.tracking) t.tracking = opts.tracking;
    if (opts.caps) t.capitalization = TextCase.ALLCAPS;
    layer.name = name;
    return layer;
}

function save(doc, file) {
    var opts = new PhotoshopSaveOptions();
    opts.layers = true;
    doc.saveAs(new File(FOLDER + "/" + file), opts, true, Extension.LOWERCASE);
}

// ---------------------------------------------------------------- copertina
var cover = newDoc("cover");
rect(cover, "IMAGE", 0, 0, W, H, C.placeholder);
scrim(cover, "Sfumatura", 520, 1350);
rect(cover, "Velatura alta", 0, 0, W, 220, C.bg, 45);
text(cover, "LABEL", "SLEEP SCIENCE", 90, 90, 900, 50, F.mono, 30, C.accent, { tracking: 120 });
text(cover, "TITLE", "Your body does this every single night", 90, 760, 900, 380, F.serif, 112, C.text, { leading: 112 });
text(cover, "HANDLE", "@you.didnot.know", 90, 1200, 500, 50, F.mono, 26, C.muted, { tracking: 60 });
text(cover, "CREDIT", "Photo: Author (CC BY 4.0)", 590, 1204, 400, 40, F.sans, 18, C.muted, { align: Justification.RIGHT });
rect(cover, "Linea", 90, 1180, 170, 1183, C.accent);
save(cover, "cover.psd");

// ---------------------------------------------------------------- slide interne
var slide = newDoc("slide");
rect(slide, "IMAGE", 0, 0, W, 720, C.placeholder);
scrim(slide, "Sfumatura", 380, 722);
text(slide, "NUMBER", "02/06", 840, 60, 150, 44, F.mono, 26, C.text, { align: Justification.RIGHT, tracking: 80 });
text(slide, "CREDIT", "Photo: Author (CC BY 4.0)", 590, 680, 400, 30, F.sans, 16, C.muted, { align: Justification.RIGHT });
text(slide, "LABEL", "SCIENCE", 90, 740, 900, 40, F.mono, 26, C.accent, { tracking: 120 });
text(slide, "HIGHLIGHT", "+1 cm", 86, 780, 900, 150, F.serifItalic, 130, C.accent);
text(slide, "TITLE", "You get taller", 90, 930, 900, 130, F.serif, 76, C.text, { leading: 78 });
text(slide, "BODY", "At night the discs in your spine rehydrate. In the morning you are about one centimeter taller than in the evening.", 90, 1070, 900, 210, F.sans, 36, C.muted, { leading: 48 });
text(slide, "HANDLE", "@you.didnot.know", 90, 1290, 500, 40, F.mono, 22, C.muted, { tracking: 60 });
save(slide, "slide.psd");

// ---------------------------------------------------------------- ultima slide
var end = newDoc("end");
rect(end, "Luce", 0, 0, W, H, "14161D", 100);
text(end, "LABEL", "YOU DID NOT KNOW", 90, 90, 900, 50, F.mono, 28, C.accent, { tracking: 120 });
text(end, "TITLE", "Save this and send it to someone who never sleeps enough", 90, 300, 900, 560, F.serif, 120, C.text, { leading: 122 });
rect(end, "Linea", 90, 1060, 170, 1063, C.accent);
text(end, "HANDLE", "@you.didnot.know", 90, 1090, 900, 60, F.mono, 40, C.text, { tracking: 60 });
text(end, "BODY", "a new mind-blowing fact every day", 90, 1160, 900, 60, F.sans, 32, C.muted);
save(end, "end.psd");

app.preferences.rulerUnits = oldUnits;
app.preferences.typeUnits = oldType;
alert("Fatto: cover.psd, slide.psd ed end.psd sono nella cartella dello script.");
