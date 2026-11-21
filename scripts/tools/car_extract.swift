// car_extract.swift: export every image, vector, icon, color and data asset
// from the compiled asset catalog (Assets.car) of a macOS bundle.
//
// Uses only public AppKit APIs (Bundle.image(forResource:), NSColor(named:),
// NSDataAsset). Asset names come from `assetutil --info`.
//
// usage: swift car_extract.swift <bundle-path> <assetutil-info.json> <out-dir>

import AppKit
import Foundation

let args = CommandLine.arguments
guard args.count == 4, let bundle = Bundle(path: args[1]) else {
    FileHandle.standardError.write("usage: car_extract <bundle> <info.json> <out>\n".data(using: .utf8)!)
    exit(2)
}
let info = try JSONSerialization.jsonObject(with: Data(contentsOf: URL(fileURLWithPath: args[2]))) as! [[String: Any]]
let out = URL(fileURLWithPath: args[3])
let fm = FileManager.default

func dir(_ name: String) -> URL {
    let u = out.appendingPathComponent(name)
    try? fm.createDirectory(at: u, withIntermediateDirectories: true)
    return u
}

func safe(_ s: String) -> String {
    s.replacingOccurrences(of: "/", with: "_").replacingOccurrences(of: ":", with: "_")
}

/// Render an NSImage to PNG at a given scale, in a given appearance.
func png(_ image: NSImage, scale: CGFloat, appearance: NSAppearance) -> Data? {
    let size = image.size
    guard size.width > 0, size.height > 0 else { return nil }
    let w = Int((size.width * scale).rounded()), h = Int((size.height * scale).rounded())
    guard let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: w, pixelsHigh: h,
                                     bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true,
                                     isPlanar: false, colorSpaceName: .deviceRGB,
                                     bytesPerRow: 0, bitsPerPixel: 0) else { return nil }
    rep.size = size
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)
    appearance.performAsCurrentDrawingAppearance {
        image.draw(in: NSRect(origin: .zero, size: size))
    }
    NSGraphicsContext.restoreGraphicsState()
    return rep.representation(using: .png, properties: [:])
}

/// Render an NSImage into a single-page PDF (keeps vectors vector).
func pdf(_ image: NSImage) -> Data? {
    let data = NSMutableData()
    var box = CGRect(origin: .zero, size: image.size)
    guard box.width > 0, let consumer = CGDataConsumer(data: data as CFMutableData),
          let ctx = CGContext(consumer: consumer, mediaBox: &box, nil) else { return nil }
    ctx.beginPDFPage(nil)
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = NSGraphicsContext(cgContext: ctx, flipped: false)
    image.draw(in: box)
    NSGraphicsContext.restoreGraphicsState()
    ctx.endPDFPage()
    ctx.closePDF()
    return data as Data
}

func rgba(_ c: NSColor?) -> [String: Any]? {
    guard let c = c?.usingColorSpace(.sRGB) else { return nil }
    let hex = String(format: "#%02X%02X%02X", Int((c.redComponent * 255).rounded()),
                     Int((c.greenComponent * 255).rounded()), Int((c.blueComponent * 255).rounded()))
    return ["hex": hex, "alpha": String(format: "%.3g", c.alphaComponent)]
}

let light = NSAppearance(named: .aqua)!, dark = NSAppearance(named: .darkAqua)!
var colors: [String: Any] = [:]
var done = Set<String>()
var counts: [String: Int] = [:]

for asset in info.dropFirst() {
    guard let name = asset["Name"] as? String, let type = asset["AssetType"] as? String else { continue }
    if name.hasPrefix("ZZZZPacked") { continue }        // atlas pages; members are exported by name
    let key = type + "/" + name
    if done.contains(key) { continue }
    done.insert(key)

    switch type {
    case "Color":
        var entry: [String: Any] = [:]
        if let c = NSColor(named: name, bundle: bundle) {
            light.performAsCurrentDrawingAppearance { entry["light"] = rgba(c) }
            dark.performAsCurrentDrawingAppearance { entry["dark"] = rgba(c) }
        }
        colors[name] = entry
        counts["color", default: 0] += 1

    case "Data":
        if let d = NSDataAsset(name: name, bundle: bundle) {
            let ext = d.typeIdentifier.components(separatedBy: ".").last ?? "bin"
            try? d.data.write(to: dir("data").appendingPathComponent(safe(name) + "." + ext))
            counts["data", default: 0] += 1
        }

    case "Image", "Vector", "Icon Image", "MultiSized Image", "PackedImage":
        if done.contains("img/" + name) { continue }
        done.insert("img/" + name)
        guard let img = bundle.image(forResource: name) else { continue }
        let d = dir("images")
        let n = safe(name)
        for (scale, suffix) in [(1.0, ""), (2.0, "@2x")] {
            if let p = png(img, scale: scale, appearance: light) {
                try? p.write(to: d.appendingPathComponent(n + suffix + ".png"))
            }
        }
        // Dark-appearance variant when the catalog has one.
        if (info.contains { ($0["Name"] as? String) == name && ($0["Appearance"] as? String)?.contains("Dark") == true }),
           let p = png(img, scale: 2, appearance: dark) {
            try? p.write(to: d.appendingPathComponent(n + "-dark@2x.png"))
        }
        if asset["Preserved Vector Representation"] as? Bool == true || type == "Vector",
           let v = pdf(img) {
            try? v.write(to: d.appendingPathComponent(n + ".pdf"))
        }
        counts["image", default: 0] += 1

    default:
        counts["skipped:" + type, default: 0] += 1
    }
}

if !colors.isEmpty {
    let data = try JSONSerialization.data(withJSONObject: colors, options: [.prettyPrinted, .sortedKeys])
    try data.write(to: dir(".").appendingPathComponent("colors.json"))
}
print(counts.map { "\($0.key)=\($0.value)" }.sorted().joined(separator: " "))
