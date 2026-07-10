import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import type { Zone } from '../types';

interface LiveStadiumMapProps {
  zones: Zone[];
}

// AT&T Stadium coordinates approximately
const STADIUM_CENTER: [number, number] = [32.7473, -97.0945];

// Map each zone to a relative offset to place them around the stadium
const ZONE_OFFSETS: Record<string, [number, number]> = {
  gate_a: [0.001, 0.001],
  gate_b: [-0.001, 0.001],
  gate_c: [-0.001, -0.001],
  gate_d: [0.001, -0.001],
  concourse_1: [0.0005, 0.0005],
  concourse_2: [-0.0005, -0.0005],
  fan_zone: [0, 0.002],
  transit_hub: [0.002, 0],
};

function getDensityColor(density: number) {
  if (density < 0.4) return '#22c55e'; // green
  if (density < 0.7) return '#eab308'; // yellow
  if (density < 0.9) return '#f97316'; // orange
  return '#ef4444'; // red
}

export function LiveStadiumMap({ zones }: LiveStadiumMapProps) {
  return (
    <div
      style={{
        height: '300px',
        width: '100%',
        borderRadius: '0.75rem',
        overflow: 'hidden',
      }}
    >
      <MapContainer
        center={STADIUM_CENTER}
        zoom={16}
        style={{ height: '100%', width: '100%' }}
        zoomControl={false}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          className="map-tiles"
        />
        {zones.map((zone) => {
          const offset = ZONE_OFFSETS[zone.name] || [0, 0];
          const position: [number, number] = [
            STADIUM_CENTER[0] + offset[0],
            STADIUM_CENTER[1] + offset[1],
          ];
          return (
            <CircleMarker
              key={zone.name}
              center={position}
              pathOptions={{
                color: getDensityColor(zone.density),
                fillColor: getDensityColor(zone.density),
                fillOpacity: 0.7,
              }}
              radius={zone.density * 30 + 10}
            >
              <Popup>
                <strong>{zone.label || zone.name.replace('_', ' ')}</strong>
                <br />
                Density: {Math.round(zone.density * 100)}%
              </Popup>
            </CircleMarker>
          );
        })}
      </MapContainer>
    </div>
  );
}
