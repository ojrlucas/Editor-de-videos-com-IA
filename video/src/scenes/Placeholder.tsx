import React from 'react';
export const Placeholder: React.FC<{name: string}> = ({name}) => <div style={{position: 'absolute', inset: 0, color: '#fff', fontSize: 80}}>{name}</div>;
