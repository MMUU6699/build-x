'use strict';
const MANIFEST = 'flutter-app-manifest';
const TEMP = 'flutter-temp-cache';
const CACHE_NAME = 'flutter-app-cache';

const RESOURCES = {"assets/AssetManifest.bin": "5aae359d9c05878fa1cc189827da3e66",
"assets/AssetManifest.bin.json": "10fdcff84b14a2e20c7fc7c4dab309e1",
"assets/assets/app_icon.ico": "0a98dde72119a69db1ce04ea8e53a519",
"assets/assets/app_icon.png": "99a77bae7884bf5ba4d65e92e0fb0c40",
"assets/assets/html/mark.html": "c32a4481431a452ba4b92cf00f3072d9",
"assets/assets/icons/302ai-color.svg": "78f2202c22048c9d9246114ff5bfa5b0",
"assets/assets/icons/aihubmix-color.svg": "9961f61d85b755eebc890a6d274040f2",
"assets/assets/icons/alibabacloud-color.svg": "ff035bf78d5ba1cab5bd84f200fb01b4",
"assets/assets/icons/anthropic.svg": "4752173e6ad2c7cb5e8ead6938646380",
"assets/assets/icons/bing-color.svg": "41149db1f5bd184f4da55fd46dbfa8cd",
"assets/assets/icons/bing.png": "ea8f00001278e0b29a5d2ba1e8f4fcbb",
"assets/assets/icons/bocha-color.svg": "84303fff0c40a6ade921438fc3c4e93a",
"assets/assets/icons/brave-color.svg": "45da897bbdc50a9caa622f9cc9d5995e",
"assets/assets/icons/bytedance-color.svg": "26554d835b8da2b686f6b266ec05ba91",
"assets/assets/icons/claude-color.svg": "b37d68ab86d1701a30d5bd956b7dd058",
"assets/assets/icons/cloudflare-color.svg": "137d8a62a38b4df419d7aa102eb71444",
"assets/assets/icons/codex.svg": "e96b66795373820d54a4e961c75fb300",
"assets/assets/icons/cohere-color.svg": "b303b0cbd0334ecec9324f086b68a7ac",
"assets/assets/icons/deepseek-color.svg": "e79363c865a1f098e0e87550862815f5",
"assets/assets/icons/deepthink.svg": "e69f21716b80f6e8f208bc8ae66fee34",
"assets/assets/icons/deepthink__.svg": "bf1080c2beacd20ed05a721383d2d52c",
"assets/assets/icons/discord.svg": "08f7e1506f35fd768cdcb192b022a6f3",
"assets/assets/icons/doubao-color.svg": "23df27e021b43f8f13ec55923d95950c",
"assets/assets/icons/duckduckgo-color.svg": "d51162b178bfe70639014a2261a1c2ca",
"assets/assets/icons/exa-color.svg": "8ecd44cc06c2ffd61e4998c0bba9c85e",
"assets/assets/icons/exa.png": "3b112b2392f0683398107e91e82802c6",
"assets/assets/icons/gemini-color.svg": "738fc28717976793bc5143d7138eae01",
"assets/assets/icons/gemma-color.svg": "019b63eccac8614ba055d9d4a28b256c",
"assets/assets/icons/github.svg": "782a26d5568b388130cccbc4361700d5",
"assets/assets/icons/google-color.svg": "c655b437e35ff9e86371a6a872499c4b",
"assets/assets/icons/google.svg": "b60914a38e6af4fe9d710f7f01e17103",
"assets/assets/icons/grok.svg": "a3e0ccafa80d83f28f2747d53604c0b1",
"assets/assets/icons/hunyuan-color.svg": "8f106c4f71894af09556210df04a2290",
"assets/assets/icons/iflow-color.svg": "8b9bf025969953dae47d0ba4bd31f066",
"assets/assets/icons/internlm-color.svg": "3176a0ddec7638670a36865e47f81a32",
"assets/assets/icons/jina-color.svg": "eabb9f342b021650c3fee528d3275742",
"assets/assets/icons/juhenext.png": "4be7beac1cb13f0a643ccbe8ba1a2071",
"assets/assets/icons/katkwaipilot-color.svg": "7bd4ac295fc91cebe11d36592c518a1d",
"assets/assets/icons/kelivo.png": "2d7b36842107243076e27e1d5406cc49",
"assets/assets/icons/kimi-color.svg": "422486debd2c13a6a57dcf1bec748e9c",
"assets/assets/icons/ling.png": "9eff6eba58195b5df9888013efbeb1e8",
"assets/assets/icons/linkup.svg": "3c5b174e87bc2604aea866444fe33c99",
"assets/assets/icons/list.svg": "c169ab08833115a5e30cf5d0ab8add6b",
"assets/assets/icons/list2.svg": "734cb4a02599f8f41436682f20eac695",
"assets/assets/icons/longcat.png": "4c1f9f537b3af23f8a69245589e4a473",
"assets/assets/icons/meta-color.svg": "1e2a824a00860184b4305311af2017c0",
"assets/assets/icons/metaso-color.svg": "5adf891520715191ca8e24c870fbb198",
"assets/assets/icons/minimax-color.svg": "b79e91c651a03521cb7a96a9d6ffa14f",
"assets/assets/icons/mistral-color.svg": "9ca07eed783cd14677a843651b941a62",
"assets/assets/icons/ollama.svg": "24bda001bd2d6a3d81e8bfbf64269fb6",
"assets/assets/icons/openai.svg": "eb2553e579562fd4fe90315108bc1f94",
"assets/assets/icons/openrouter.svg": "40645826c2812819dfeb57cf29491eb9",
"assets/assets/icons/perplexity-color.svg": "3e58e106dcabadd484cfa512ab6a3c46",
"assets/assets/icons/Powered-by-dark.png": "e8f4ddd61e082638222f2934108c4731",
"assets/assets/icons/Powered-by-light.png": "02273262624dab8e8267276fa33b146c",
"assets/assets/icons/qq.svg": "4c6b944b1797235129d15fd903a08cc2",
"assets/assets/icons/qwen-color.svg": "7a38d3851b5f3d37527456b474d75a37",
"assets/assets/icons/searxng-color.svg": "a804b72fb08302b1160eeaf971aa9f56",
"assets/assets/icons/siliconflow-color.svg": "c2c2b16a80ce31bcb2c1f580390574f1",
"assets/assets/icons/sora-color.svg": "a8f0235e36a4614d55515c59a8239e7f",
"assets/assets/icons/stepfun-color.svg": "37c371f8678ab668dfaefe20eb176756",
"assets/assets/icons/stop.svg": "a5b84cf68f370fafe9d436934ca00fdd",
"assets/assets/icons/tavily-color.svg": "ae766303d628402096eabfa057ae369f",
"assets/assets/icons/tavily.png": "76933c90f5012d01d3cf6e03b27463fb",
"assets/assets/icons/tencent-qq.svg": "0220560ed7ba6226768b3de7654eceb0",
"assets/assets/icons/tensdaq-color.svg": "db592a461fc4125007f0741f2f90bf3b",
"assets/assets/icons/web.svg": "6f2b418687ba16dcbbd4901681eedbb4",
"assets/assets/icons/xai.svg": "1b3d6c1b868528b3a5a250f7b4d9b410",
"assets/assets/icons/zhipu-color.svg": "a2c1c54f7a27cb18f80d6920eefbba0f",
"assets/assets/icons/zhipu2-color.svg": "5a0074359f73ee8b0a93ee90a90221ef",
"assets/assets/icon_mac.png": "38dd099eee0749b76de09b283871d9ec",
"assets/assets/mermaid.min.js": "26bb15190d3018c8cb1e2b3b9676966f",
"assets/FontManifest.json": "cd43f5972cec9cdf99a585e8db603ba3",
"assets/fonts/MaterialIcons-Regular.otf": "e09418e3b3f6b72d0f214b277d17aa5c",
"assets/NOTICES": "308a3dbcbbd355ca80935a94bfd3f050",
"assets/packages/cupertino_icons/assets/CupertinoIcons.ttf": "33b7d9392238c04c131b6ce224e13711",
"assets/packages/flutter_math_fork/lib/katex_fonts/fonts/KaTeX_AMS-Regular.ttf": "657a5353a553777e270827bd1630e467",
"assets/packages/flutter_math_fork/lib/katex_fonts/fonts/KaTeX_Caligraphic-Bold.ttf": "a9c8e437146ef63fcd6fae7cf65ca859",
"assets/packages/flutter_math_fork/lib/katex_fonts/fonts/KaTeX_Caligraphic-Regular.ttf": "7ec92adfa4fe03eb8e9bfb60813df1fa",
"assets/packages/flutter_math_fork/lib/katex_fonts/fonts/KaTeX_Fraktur-Bold.ttf": "46b41c4de7a936d099575185a94855c4",
"assets/packages/flutter_math_fork/lib/katex_fonts/fonts/KaTeX_Fraktur-Regular.ttf": "dede6f2c7dad4402fa205644391b3a94",
"assets/packages/flutter_math_fork/lib/katex_fonts/fonts/KaTeX_Main-Bold.ttf": "9eef86c1f9efa78ab93d41a0551948f7",
"assets/packages/flutter_math_fork/lib/katex_fonts/fonts/KaTeX_Main-BoldItalic.ttf": "e3c361ea8d1c215805439ce0941a1c8d",
"assets/packages/flutter_math_fork/lib/katex_fonts/fonts/KaTeX_Main-Italic.ttf": "ac3b1882325add4f148f05db8cafd401",
"assets/packages/flutter_math_fork/lib/katex_fonts/fonts/KaTeX_Main-Regular.ttf": "5a5766c715ee765aa1398997643f1589",
"assets/packages/flutter_math_fork/lib/katex_fonts/fonts/KaTeX_Math-BoldItalic.ttf": "946a26954ab7fbd7ea78df07795a6cbc",
"assets/packages/flutter_math_fork/lib/katex_fonts/fonts/KaTeX_Math-Italic.ttf": "a7732ecb5840a15be39e1eda377bc21d",
"assets/packages/flutter_math_fork/lib/katex_fonts/fonts/KaTeX_SansSerif-Bold.ttf": "ad0a28f28f736cf4c121bcb0e719b88a",
"assets/packages/flutter_math_fork/lib/katex_fonts/fonts/KaTeX_SansSerif-Italic.ttf": "d89b80e7bdd57d238eeaa80ed9a1013a",
"assets/packages/flutter_math_fork/lib/katex_fonts/fonts/KaTeX_SansSerif-Regular.ttf": "b5f967ed9e4933f1c3165a12fe3436df",
"assets/packages/flutter_math_fork/lib/katex_fonts/fonts/KaTeX_Script-Regular.ttf": "55d2dcd4778875a53ff09320a85a5296",
"assets/packages/flutter_math_fork/lib/katex_fonts/fonts/KaTeX_Size1-Regular.ttf": "1e6a3368d660edc3a2fbbe72edfeaa85",
"assets/packages/flutter_math_fork/lib/katex_fonts/fonts/KaTeX_Size2-Regular.ttf": "959972785387fe35f7d47dbfb0385bc4",
"assets/packages/flutter_math_fork/lib/katex_fonts/fonts/KaTeX_Size3-Regular.ttf": "e87212c26bb86c21eb028aba2ac53ec3",
"assets/packages/flutter_math_fork/lib/katex_fonts/fonts/KaTeX_Size4-Regular.ttf": "85554307b465da7eb785fd3ce52ad282",
"assets/packages/flutter_math_fork/lib/katex_fonts/fonts/KaTeX_Typewriter-Regular.ttf": "87f56927f1ba726ce0591955c8b3b42d",
"assets/packages/gpt_markdown/lib/fonts/JetBrainsMono-Regular.ttf": "d09f65145228b709a10fa0a06d522d89",
"assets/packages/lucide_icons_flutter/assets/build_font/LucideVariable-w100.ttf": "e4865d405ac7c7f9546d6aaaa67b011b",
"assets/packages/lucide_icons_flutter/assets/build_font/LucideVariable-w200.ttf": "331d8111c790ee34917f20c7bd64ab64",
"assets/packages/lucide_icons_flutter/assets/build_font/LucideVariable-w300.ttf": "68a41db340539672594ccc572b3346fb",
"assets/packages/lucide_icons_flutter/assets/build_font/LucideVariable-w400.ttf": "48ff731c717c85757e1ad7ccced1e1ec",
"assets/packages/lucide_icons_flutter/assets/build_font/LucideVariable-w500.ttf": "66878381d8309e167d4e06eb6df15458",
"assets/packages/lucide_icons_flutter/assets/build_font/LucideVariable-w600.ttf": "c1f76ff66005c93ce5ca5a4851065975",
"assets/packages/lucide_icons_flutter/assets/lucide.ttf": "dd32a9e2f8afe3b6a636dd38d6cfc83d",
"assets/shaders/ink_sparkle.frag": "ecc85a2e95f5e9f53123dcaf8cb9b6ce",
"assets/shaders/stretch_effect.frag": "40d68efbbf360632f614c731219e95f0",
"canvaskit/canvaskit.js": "8331fe38e66b3a898c4f37648aaf7ee2",
"canvaskit/canvaskit.js.symbols": "a3c9f77715b642d0437d9c275caba91e",
"canvaskit/canvaskit.wasm": "9b6a7830bf26959b200594729d73538e",
"canvaskit/chromium/canvaskit.js": "a80c765aaa8af8645c9fb1aae53f9abf",
"canvaskit/chromium/canvaskit.js.symbols": "e2d09f0e434bc118bf67dae526737d07",
"canvaskit/chromium/canvaskit.wasm": "a726e3f75a84fcdf495a15817c63a35d",
"canvaskit/skwasm.js": "8060d46e9a4901ca9991edd3a26be4f0",
"canvaskit/skwasm.js.symbols": "3a4aadf4e8141f284bd524976b1d6bdc",
"canvaskit/skwasm.wasm": "7e5f3afdd3b0747a1fd4517cea239898",
"canvaskit/skwasm_heavy.js": "740d43a6b8240ef9e23eed8c48840da4",
"canvaskit/skwasm_heavy.js.symbols": "0755b4fb399918388d71b59ad390b055",
"canvaskit/skwasm_heavy.wasm": "b0be7910760d205ea4e011458df6ee01",
"favicon.png": "f4982f520239fb2f6f515caceabf3a53",
"flutter.js": "24bc71911b75b5f8135c949e27a2984e",
"flutter_bootstrap.js": "cbef8e3d3e1898dca4d1b3a43e4765a0",
"icons/Icon-192.png": "8a0073a6737297aacfb0b87f9b2903f4",
"icons/Icon-512.png": "b334ecc79af10b3821a6a0433c655e00",
"icons/Icon-maskable-192.png": "8a0073a6737297aacfb0b87f9b2903f4",
"icons/Icon-maskable-512.png": "b334ecc79af10b3821a6a0433c655e00",
"index.html": "22da34a42050c400df71c62b9e81d86e",
"/": "22da34a42050c400df71c62b9e81d86e",
"main.dart.js": "77fc9390e5570cfc6efcacf3109dfb7c",
"manifest.json": "1b0651ce899225a2ba256688b19c2267",
"splash/img/dark-1x.png": "71dac3eb73620dfc09bfd5cfeac3ced5",
"splash/img/dark-2x.png": "5e4cdcdc9837fd516ac4b0e7aad9c883",
"splash/img/dark-3x.png": "c2f71d161cbd4a2556f7b8fffc12710f",
"splash/img/dark-4x.png": "222ea43132af2b865fc769789f125a9f",
"splash/img/light-1x.png": "71dac3eb73620dfc09bfd5cfeac3ced5",
"splash/img/light-2x.png": "5e4cdcdc9837fd516ac4b0e7aad9c883",
"splash/img/light-3x.png": "c2f71d161cbd4a2556f7b8fffc12710f",
"splash/img/light-4x.png": "222ea43132af2b865fc769789f125a9f",
"version.json": "d9f0b45d982f9395bdc0d1ccbaed0bb7"};
// The application shell files that are downloaded before a service worker can
// start.
const CORE = ["main.dart.js",
"index.html",
"flutter_bootstrap.js",
"assets/AssetManifest.bin.json",
"assets/FontManifest.json"];

// During install, the TEMP cache is populated with the application shell files.
self.addEventListener("install", (event) => {
  self.skipWaiting();
  return event.waitUntil(
    caches.open(TEMP).then((cache) => {
      return cache.addAll(
        CORE.map((value) => new Request(value, {'cache': 'reload'})));
    })
  );
});
// During activate, the cache is populated with the temp files downloaded in
// install. If this service worker is upgrading from one with a saved
// MANIFEST, then use this to retain unchanged resource files.
self.addEventListener("activate", function(event) {
  return event.waitUntil(async function() {
    try {
      var contentCache = await caches.open(CACHE_NAME);
      var tempCache = await caches.open(TEMP);
      var manifestCache = await caches.open(MANIFEST);
      var manifest = await manifestCache.match('manifest');
      // When there is no prior manifest, clear the entire cache.
      if (!manifest) {
        await caches.delete(CACHE_NAME);
        contentCache = await caches.open(CACHE_NAME);
        for (var request of await tempCache.keys()) {
          var response = await tempCache.match(request);
          await contentCache.put(request, response);
        }
        await caches.delete(TEMP);
        // Save the manifest to make future upgrades efficient.
        await manifestCache.put('manifest', new Response(JSON.stringify(RESOURCES)));
        // Claim client to enable caching on first launch
        self.clients.claim();
        return;
      }
      var oldManifest = await manifest.json();
      var origin = self.location.origin;
      for (var request of await contentCache.keys()) {
        var key = request.url.substring(origin.length + 1);
        if (key == "") {
          key = "/";
        }
        // If a resource from the old manifest is not in the new cache, or if
        // the MD5 sum has changed, delete it. Otherwise the resource is left
        // in the cache and can be reused by the new service worker.
        if (!RESOURCES[key] || RESOURCES[key] != oldManifest[key]) {
          await contentCache.delete(request);
        }
      }
      // Populate the cache with the app shell TEMP files, potentially overwriting
      // cache files preserved above.
      for (var request of await tempCache.keys()) {
        var response = await tempCache.match(request);
        await contentCache.put(request, response);
      }
      await caches.delete(TEMP);
      // Save the manifest to make future upgrades efficient.
      await manifestCache.put('manifest', new Response(JSON.stringify(RESOURCES)));
      // Claim client to enable caching on first launch
      self.clients.claim();
      return;
    } catch (err) {
      // On an unhandled exception the state of the cache cannot be guaranteed.
      console.error('Failed to upgrade service worker: ' + err);
      await caches.delete(CACHE_NAME);
      await caches.delete(TEMP);
      await caches.delete(MANIFEST);
    }
  }());
});
// The fetch handler redirects requests for RESOURCE files to the service
// worker cache.
self.addEventListener("fetch", (event) => {
  if (event.request.method !== 'GET') {
    return;
  }
  var origin = self.location.origin;
  var key = event.request.url.substring(origin.length + 1);
  // Redirect URLs to the index.html
  if (key.indexOf('?v=') != -1) {
    key = key.split('?v=')[0];
  }
  if (event.request.url == origin || event.request.url.startsWith(origin + '/#') || key == '') {
    key = '/';
  }
  // If the URL is not the RESOURCE list then return to signal that the
  // browser should take over.
  if (!RESOURCES[key]) {
    return;
  }
  // If the URL is the index.html, perform an online-first request.
  if (key == '/') {
    return onlineFirst(event);
  }
  event.respondWith(caches.open(CACHE_NAME)
    .then((cache) =>  {
      return cache.match(event.request).then((response) => {
        // Either respond with the cached resource, or perform a fetch and
        // lazily populate the cache only if the resource was successfully fetched.
        return response || fetch(event.request).then((response) => {
          if (response && Boolean(response.ok)) {
            cache.put(event.request, response.clone());
          }
          return response;
        });
      })
    })
  );
});
self.addEventListener('message', (event) => {
  // SkipWaiting can be used to immediately activate a waiting service worker.
  // This will also require a page refresh triggered by the main worker.
  if (event.data === 'skipWaiting') {
    self.skipWaiting();
    return;
  }
  if (event.data === 'downloadOffline') {
    downloadOffline();
    return;
  }
});
// Download offline will check the RESOURCES for all files not in the cache
// and populate them.
async function downloadOffline() {
  var resources = [];
  var contentCache = await caches.open(CACHE_NAME);
  var currentContent = {};
  for (var request of await contentCache.keys()) {
    var key = request.url.substring(origin.length + 1);
    if (key == "") {
      key = "/";
    }
    currentContent[key] = true;
  }
  for (var resourceKey of Object.keys(RESOURCES)) {
    if (!currentContent[resourceKey]) {
      resources.push(resourceKey);
    }
  }
  return contentCache.addAll(resources);
}
// Attempt to download the resource online before falling back to
// the offline cache.
function onlineFirst(event) {
  return event.respondWith(
    fetch(event.request).then((response) => {
      return caches.open(CACHE_NAME).then((cache) => {
        cache.put(event.request, response.clone());
        return response;
      });
    }).catch((error) => {
      return caches.open(CACHE_NAME).then((cache) => {
        return cache.match(event.request).then((response) => {
          if (response != null) {
            return response;
          }
          throw error;
        });
      });
    })
  );
}
