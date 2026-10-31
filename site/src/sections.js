// The sections of TechVerse. Auric may add new ones (they then come from meta/index.sections).
export const SECTIONS = [
  { id: 'ai', name: 'AI & Machine Learning', icon: '🧠', color: '#8b7cff', blurb: 'How machines learn, see, talk and decide.' },
  { id: 'hardware', name: 'Computers & Hardware', icon: '🖥️', color: '#4aa8ff', blurb: 'Chips, memory, screens: what is inside a computer.' },
  { id: 'programming', name: 'Programming', icon: '⌨️', color: '#3ddc97', blurb: 'Languages, algorithms and how software is built.' },
  { id: 'internet', name: 'Internet & Networks', icon: '🌐', color: '#2ec4d6', blurb: 'How data travels across the world in milliseconds.' },
  { id: 'security', name: 'Cybersecurity', icon: '🔐', color: '#ff6b6b', blurb: 'Keeping data and people safe online.' },
  { id: 'space', name: 'Space Tech', icon: '🚀', color: '#a78bfa', blurb: 'Rockets, satellites and telescopes.' },
  { id: 'robotics', name: 'Robotics', icon: '🤖', color: '#f59e0b', blurb: 'Machines that sense and move.' },
  { id: 'gadgets', name: 'Phones & Gadgets', icon: '📱', color: '#38bdf8', blurb: 'The devices in our pockets and homes.' },
  { id: 'energy', name: 'Energy & Green Tech', icon: '⚡', color: '#84cc16', blurb: 'Batteries, solar power and clean energy.' },
  { id: 'biotech', name: 'Biotech & Health Tech', icon: '🧬', color: '#f472b6', blurb: 'Technology for medicine and life science.' },
  { id: 'gaming', name: 'Gaming', icon: '🎮', color: '#fb7185', blurb: 'How games and consoles work.' },
  { id: 'transport', name: 'Cars & Transport', icon: '🚗', color: '#fbbf24', blurb: 'Engines, electric cars, trains and planes.' },
  { id: 'history', name: 'History of Tech', icon: '📜', color: '#c4a484', blurb: 'The inventions that changed everything.' },
  { id: 'future', name: 'Future Tech', icon: '🔮', color: '#22d3ee', blurb: 'What researchers are building next.' },
];
export const sectionById = (id, extra = []) => [...SECTIONS, ...extra].find((s) => s.id === id)
  || { id, name: id, icon: '✨', color: '#94a3b8', blurb: '' };
