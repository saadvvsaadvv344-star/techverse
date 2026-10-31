import { Component } from 'react';

/** One of Auric's components failing never breaks the page: it just disappears (and the self-test reports it). */
export class Safe extends Component {
  constructor(p) { super(p); this.state = { err: null }; }
  static getDerivedStateFromError(err) { return { err }; }
  componentDidCatch(err) { (window.__tvErrors = window.__tvErrors || []).push(`${this.props.name}: ${err && err.message}`); }
  render() { return this.state.err ? null : this.props.children; }
}
