// Capture only the visible Linux RViz window for a local validation artifact.
// Build in WSL: g++ tools/capture_rviz.cpp -lX11 -lz -o /tmp/igvc-capture-rviz
#include <X11/Xlib.h>
#include <X11/Xutil.h>
#include <zlib.h>
#include <algorithm>
#include <cctype>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

std::string titleFilter = "rviz";

Window findRviz(Display* display, Window window) {
    char* name = nullptr;
    if (XFetchName(display, window, &name) && name) {
        std::string title(name); XFree(name);
        std::transform(title.begin(), title.end(), title.begin(), [](unsigned char c) { return std::tolower(c); });
        XWindowAttributes info{};
        if (title.find(titleFilter) != std::string::npos && XGetWindowAttributes(display, window, &info)
            && info.map_state == IsViewable && info.width > 400 && info.height > 300) return window;
    }
    Window root, parent, *children = nullptr; unsigned count = 0;
    if (!XQueryTree(display, window, &root, &parent, &children, &count)) return 0;
    Window found = 0;
    for (unsigned i = 0; i < count && !found; ++i) found = findRviz(display, children[i]);
    if (children) XFree(children);
    return found;
}
void integer(std::ostream& out, uint32_t value) {
    for (int i = 3; i >= 0; --i) out.put(static_cast<char>((value >> (8 * i)) & 255));
}
void chunk(std::ostream& out, const char* type, const std::vector<unsigned char>& bytes) {
    integer(out, bytes.size()); out.write(type, 4);
    out.write(reinterpret_cast<const char*>(bytes.data()), bytes.size());
    uLong crc = crc32(0, reinterpret_cast<const Bytef*>(type), 4);
    if (!bytes.empty()) crc = crc32(crc, bytes.data(), bytes.size());
    integer(out, crc);
}
int main(int argc, char** argv) {
    if (argc < 2 || argc > 3) { std::cerr << "Usage: capture-rviz output.png [window-title-substring]\n"; return 2; }
    if (argc == 3) { titleFilter = argv[2]; std::transform(titleFilter.begin(), titleFilter.end(), titleFilter.begin(), [](unsigned char c) { return std::tolower(c); }); }
    Display* display = XOpenDisplay(nullptr);
    if (!display) { std::cerr << "No X11 display\n"; return 1; }
    Window window = findRviz(display, DefaultRootWindow(display));
    if (!window) { std::cerr << "No visible RViz window\n"; XCloseDisplay(display); return 1; }
    XWindowAttributes info{}; XGetWindowAttributes(display, window, &info);
    XImage* image = XGetImage(display, window, 0, 0, info.width, info.height, AllPlanes, ZPixmap);
    if (!image) { XCloseDisplay(display); return 1; }
    auto component = [](unsigned long pixel, unsigned long mask) {
        if (!mask) return static_cast<unsigned char>(0);
        while (!(mask & 1)) { pixel >>= 1; mask >>= 1; }
        return static_cast<unsigned char>((pixel & mask) * 255 / mask);
    };
    std::vector<unsigned char> rows;
    rows.reserve((info.width * 3 + 1) * info.height);
    for (int y = 0; y < info.height; ++y) {
        rows.push_back(0);
        for (int x = 0; x < info.width; ++x) {
            auto p = XGetPixel(image, x, y);
            rows.push_back(component(p, image->red_mask));
            rows.push_back(component(p, image->green_mask));
            rows.push_back(component(p, image->blue_mask));
        }
    }
    XDestroyImage(image); XCloseDisplay(display);
    uLongf size = compressBound(rows.size()); std::vector<unsigned char> compressed(size);
    if (compress2(compressed.data(), &size, rows.data(), rows.size(), 6) != Z_OK) return 1;
    compressed.resize(size);
    std::ofstream output(argv[1], std::ios::binary);
    output.write("\x89PNG\r\n\x1a\n", 8);
    std::vector<unsigned char> header;
    for (uint32_t v : {static_cast<uint32_t>(info.width), static_cast<uint32_t>(info.height)})
        for (int i = 3; i >= 0; --i) header.push_back((v >> (8 * i)) & 255);
    for (int v : {8, 2, 0, 0, 0}) header.push_back(v);
    chunk(output, "IHDR", header); chunk(output, "IDAT", compressed); chunk(output, "IEND", {});
    std::cout << "Captured RViz " << info.width << "x" << info.height << "\n";
    return output.good() ? 0 : 1;
}
