/*
 * Off-screen WebView that draws the comics slides on-device.
 *
 * Give it `data` (from comicvine.js, with cover images already inlined as
 * base64 by the caller) and an `onSlides(slidesObj)` / `onError(msg)` callback.
 * It loads the self-contained renderer HTML, posts the data in, and reports the
 * finished slides back as { name: "data:image/jpeg;base64,..." }.
 *
 * The WebView is rendered 1x1 and invisible — it is a rendering engine, not UI.
 */
import { useRef, useEffect, useState } from 'react';
import { View } from 'react-native';
import { WebView } from 'react-native-webview';
import { RENDERER_HTML } from './rendererHtml';

export default function ComicsRenderer({ data, onSlides, onError }) {
  const ref = useRef(null);
  const [ready, setReady] = useState(false);
  const sent = useRef(false);

  // Once the renderer signals ready AND we have data, post it in (once).
  useEffect(() => {
    if (ready && data && !sent.current && ref.current) {
      sent.current = true;
      ref.current.postMessage(JSON.stringify({ type: 'render', data }));
    }
  }, [ready, data]);

  const onMessage = (event) => {
    let msg;
    try { msg = JSON.parse(event.nativeEvent.data); } catch { return; }
    if (msg.type === 'ready') setReady(true);
    else if (msg.type === 'slides') onSlides && onSlides(msg.slides);
    else if (msg.type === 'error') onError && onError(msg.error);
  };

  return (
    <View style={{ width: 1, height: 1, opacity: 0, position: 'absolute' }} pointerEvents="none">
      <WebView
        ref={ref}
        originWhitelist={['*']}
        source={{ html: RENDERER_HTML }}
        onMessage={onMessage}
        javaScriptEnabled
        // Large data URIs render faster with hardware acceleration off on some devices.
        androidLayerType="software"
        onError={(e) => onError && onError('WebView error: ' + (e.nativeEvent && e.nativeEvent.description))}
      />
    </View>
  );
}
